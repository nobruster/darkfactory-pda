package com.northwindpay.legacy.type05;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.northwindpay.legacy.core.ArtifactGateway;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.Configuration;
import com.northwindpay.legacy.core.ProcessingContext;
import com.northwindpay.legacy.core.ProcessorDispatcher;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;
import com.northwindpay.legacy.core.StableJson;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Canonical vectors and adversarial closed-boundary checks for Type 05.
 */
class Type05ProcessorTest {
    private static final String HEADER = String.join(";",
            "assessment_id",
            "batch_id",
            "merchant_id",
            "merchant_tax_id",
            "fee_code",
            "description",
            "gross_amount_brl",
            "rate_percent",
            "assessed_fee_brl",
            "assessment_date");

    @Test
    void canonicalAcceptedScenariosMatchExactUtf8BytesAndHashes()
            throws Exception {
        for (Scenario scenario : acceptedScenarios()) {
            byte[] raw = fixtureBytes(scenario.source());
            String filename = filename(scenario);
            Type05Processor.ParsedBatch parsed =
                    Type05Processor.parseRaw(
                            raw,
                            filename,
                            scenario.batchId());
            Type05Processor.validateSourceControls(
                    parsed,
                    manifest(scenario, raw));
            Type05Processor.CsvOutput output =
                    Type05Processor.renderCsv(parsed, filename);

            assertArrayEquals(
                    fixtureBytes(scenario.expectedCsv()),
                    output.bytes(),
                    scenario.source());
            assertEquals(
                    scenario.csvSha256(),
                    ArtifactIO.sha256(output.bytes()),
                    scenario.source());
            assertEquals(scenario.rowCount(), output.rowCount());
            assertEquals(scenario.gross(), money(output.grossAmount()));
            assertEquals(
                    scenario.assessed(),
                    money(output.assessedFee()));
            assertEquals(
                    scenario.calculated(),
                    money(output.calculatedFee()));
            String rendered = new String(
                    output.bytes(),
                    StandardCharsets.UTF_8);
            assertEquals(
                    Normalizer.normalize(rendered, Normalizer.Form.NFC),
                    rendered);
            assertTrue(rendered.endsWith("\n"));
            assertFalse(rendered.endsWith("\n\n"));
            assertFalse(rendered.contains("\r"));
        }

        String minimal = new String(
                fixtureBytes("expected-sanitized.csv"),
                StandardCharsets.UTF_8);
        assertTrue(minimal.contains(
                "\"Tarifa \"\"VIP\"\"; julho, lote A\""));
        assertTrue(minimal.contains("Arredondamento mínimo"));
        String ties = new String(
                fixtureBytes(
                        "expected-rounding-half-up-sanitized.csv"),
                StandardCharsets.UTF_8);
        assertTrue(ties.contains(",0.01,0.01,"));
        assertTrue(ties.contains(",0.03,0.03,"));
    }

    @Test
    void malformedAndDarkFactoryOutcomesExposeOnlyApprovedEvidence()
            throws Exception {
        Scenario malformedScenario = malformedScenario();
        ProcessorException malformed = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.parseRaw(
                        fixtureBytes(malformedScenario.source()),
                        filename(malformedScenario),
                        malformedScenario.batchId()));
        assertEquals("INVALID_CSV_QUOTING", malformed.code());
        assertEquals(2, malformed.recordNumber());

        Scenario darkFactory = darkFactoryScenario();
        byte[] raw = fixtureBytes(darkFactory.source());
        Type05Processor.ParsedBatch parsed =
                Type05Processor.parseRaw(
                        raw,
                        filename(darkFactory),
                        darkFactory.batchId());
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.validateSourceControls(
                        parsed,
                        manifest(darkFactory, raw)));
        assertEquals(
                "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
                exception.code());
        assertEquals(1, exception.declaredRowCount());
        assertEquals(1, exception.computedRowCount());
        assertEquals("100.00", exception.declaredGrossAmount());
        assertEquals("100.00", exception.computedGrossAmount());
        assertEquals("0.99", exception.declaredAssessedFee());
        assertEquals("1.00", exception.computedAssessedFee());
        assertEquals("1.00", exception.declaredCalculatedFee());
        assertEquals("1.00", exception.computedCalculatedFee());

        Map<String, Object> evidence = ProcessorResult.rejected(
                darkFactory.batchId(),
                "05",
                exception).asMap();
        assertEquals("rejected", evidence.get("status"));
        assertEquals(
                List.of(
                        "batch_id",
                        "code",
                        "computed_assessed_fee",
                        "computed_calculated_fee",
                        "computed_gross_amount",
                        "computed_row_count",
                        "declared_assessed_fee",
                        "declared_calculated_fee",
                        "declared_gross_amount",
                        "declared_row_count",
                        "record_number",
                        "status"),
                evidence.keySet().stream().toList());
        String serialized = StableJson.line(evidence);
        assertFalse(serialized.contains("11222333000181"));
        assertFalse(serialized.contains("Tarifa divergente"));
        assertFalse(serialized.contains("**********"));
    }

    @Test
    void everyDeclaredRejectionPhaseHasExecutableCoverage()
            throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] valid = fixtureBytes(scenario.source());
        List<String> lines = lines(valid);
        String first = lines.get(1);
        String second = lines.get(2);
        Map<String, byte[]> cases = new LinkedHashMap<>();

        cases.put("INVALID_SOURCE_SIZE", new byte[5_130_139]);
        byte[] invalidUtf8 = valid.clone();
        invalidUtf8[0] = (byte) 0xff;
        cases.put("INVALID_UTF8", invalidUtf8);
        cases.put(
                "INVALID_UNICODE_NORMALIZATION",
                text(valid).replace(
                        "mínimo",
                        "mi\u0301nimo").getBytes(StandardCharsets.UTF_8));
        cases.put(
                "INVALID_TRANSPORT",
                text(valid).replaceFirst("\\n", "\r\n")
                        .getBytes(StandardCharsets.UTF_8));
        cases.put(
                "INVALID_RECORD_LENGTH",
                (HEADER + "\n" + "X".repeat(513) + "\n")
                        .getBytes(StandardCharsets.UTF_8));
        cases.put(
                "INVALID_HEADER",
                text(valid).replaceFirst(
                        "assessment_id;",
                        "assessment_ix;")
                        .getBytes(StandardCharsets.UTF_8));
        cases.put(
                "INVALID_CSV_QUOTING",
                fixtureBytes("malformed.csv"));
        cases.put(
                "INVALID_FIELD_COUNT",
                replaceLine(lines, 1, first + ";EXTRA"));
        cases.put(
                "INVALID_FIELD",
                replaceLine(
                        lines,
                        1,
                        first.replace(";1000,00;", ";1000.00;")));
        cases.put(
                "INVALID_DOCUMENT",
                replaceLine(
                        lines,
                        1,
                        first.replace(
                                "12345678000195",
                                "11111111111111")));
        cases.put(
                "INVALID_IDENTIFIER",
                replaceLine(
                        lines,
                        1,
                        first.replace(
                                "FEE2026072304001",
                                "1EE2026072304001")));
        cases.put(
                "INVALID_DESCRIPTION",
                replaceLine(
                        lines,
                        1,
                        description(first, "=FORMULA")));
        cases.put(
                "INVALID_BUSINESS_DATE",
                replaceLine(
                        lines,
                        1,
                        first.replace(
                                "23/07/2026",
                                "22/07/2026")));
        cases.put(
                "DUPLICATE_IDENTIFIER",
                replaceLine(
                        lines,
                        2,
                        second.replace(
                                "FEE2026072304002",
                                "FEE2026072304001")));
        cases.put(
                "FEE_CALCULATION_MISMATCH",
                replaceLine(
                        lines,
                        1,
                        first.replace(";12,35;", ";12,34;")));

        for (Map.Entry<String, byte[]> entry : cases.entrySet()) {
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type05Processor.parseRaw(
                            entry.getValue(),
                            filename(scenario),
                            scenario.batchId()),
                    entry.getKey());
            assertEquals(entry.getKey(), exception.code());
        }

        Type05Processor.ParsedBatch parsed =
                Type05Processor.parseRaw(
                        valid,
                        filename(scenario),
                        scenario.batchId());
        Map<String, Object> controlMutations = Map.of(
                "SOURCE_CONTROL_COUNT_MISMATCH",
                Map.entry("row_count", 3),
                "SOURCE_CONTROL_GROSS_MISMATCH",
                Map.entry("gross_amount", "1001.01"),
                "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
                Map.entry("assessed_fee", "12.35"),
                "SOURCE_CONTROL_CALCULATED_FEE_MISMATCH",
                Map.entry("calculated_fee", "12.35"));
        for (Map.Entry<String, Object> item
                : controlMutations.entrySet()) {
            @SuppressWarnings("unchecked")
            Map.Entry<String, Object> mutation =
                    (Map.Entry<String, Object>) item.getValue();
            ObjectNode changed = manifest(scenario, valid).deepCopy();
            ObjectNode controls = (ObjectNode) changed.path(
                    "source_controls");
            if (mutation.getValue() instanceof Integer integer) {
                controls.put(mutation.getKey(), integer);
            } else {
                controls.put(
                        mutation.getKey(),
                        mutation.getValue().toString());
            }
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type05Processor.validateSourceControls(
                            parsed,
                            changed));
            assertEquals(item.getKey(), exception.code());
        }
    }

    @Test
    void rejectionPrecedenceIsGlobalAndStable() throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] valid = fixtureBytes(scenario.source());
        List<String> lines = lines(valid);
        List<String> quoteAndCountLines = new ArrayList<>(lines);
        quoteAndCountLines.set(1, lines.get(1) + ";EXTRA");
        quoteAndCountLines.set(
                2,
                lines.get(2).replace(
                        ";\"Arredondamento mínimo\";",
                        ";Arredondamento mínimo;"));
        ProcessorException quoteWins = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.parseRaw(
                        join(quoteAndCountLines),
                        filename(scenario),
                        scenario.batchId()));
        assertEquals("INVALID_CSV_QUOTING", quoteWins.code());

        String fieldAndDocument = lines.get(1)
                .replace(";1000,00;", ";1000.00;")
                .replace("12345678000195", "11111111111111");
        ProcessorException fieldWins = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.parseRaw(
                        replaceLine(lines, 1, fieldAndDocument),
                        filename(scenario),
                        scenario.batchId()));
        assertEquals("INVALID_FIELD", fieldWins.code());

        byte[] bomAndTransport = new byte[valid.length + 3];
        System.arraycopy(
                new byte[]{(byte) 0xef, (byte) 0xbb, (byte) 0xbf},
                0,
                bomAndTransport,
                0,
                3);
        System.arraycopy(valid, 0, bomAndTransport, 3, valid.length);
        bomAndTransport[bomAndTransport.length - 1] = '\r';
        ProcessorException utf8Wins = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.parseRaw(
                        bomAndTransport,
                        filename(scenario),
                        scenario.batchId()));
        assertEquals("INVALID_UTF8", utf8Wins.code());

        Type05Processor.ParsedBatch parsed =
                Type05Processor.parseRaw(
                        valid,
                        filename(scenario),
                        scenario.batchId());
        ObjectNode controls = manifest(scenario, valid).deepCopy();
        ObjectNode values = (ObjectNode) controls.path("source_controls");
        values.put("row_count", 3);
        values.put("gross_amount", "1001.01");
        values.put("assessed_fee", "12.35");
        values.put("calculated_fee", "12.35");
        assertControlCode(
                parsed,
                controls,
                "SOURCE_CONTROL_COUNT_MISMATCH");
        values.put("row_count", 2);
        assertControlCode(
                parsed,
                controls,
                "SOURCE_CONTROL_GROSS_MISMATCH");
        values.put("gross_amount", "1001.00");
        assertControlCode(
                parsed,
                controls,
                "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH");
        values.put("assessed_fee", "12.36");
        assertControlCode(
                parsed,
                controls,
                "SOURCE_CONTROL_CALCULATED_FEE_MISMATCH");
    }

    @Test
    void localeDecimalsAndNegativeZeroFailClosed() throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] valid = fixtureBytes(scenario.source());
        List<String> lines = lines(valid);
        String first = lines.get(1);
        List<Map.Entry<String, String>> mutations = List.of(
                Map.entry(";1000,00;", ";1000.00;"),
                Map.entry(";1000,00;", ";+1000,00;"),
                Map.entry(";1000,00;", ";1.000,00;"),
                Map.entry(";1000,00;", ";1E3,00;"),
                Map.entry(";1000,00;", ";1000,0;"),
                Map.entry(";1000,00;", ";01000,00;"),
                Map.entry(";1000,00;", ";-0,00;"),
                Map.entry(";1,235;", ";0,000;"),
                Map.entry(";1,235;", ";100,001;"),
                Map.entry(";12,35;", ";-12,35;"),
                Map.entry(";12,35;", ";-0,00;"));
        for (Map.Entry<String, String> mutation : mutations) {
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type05Processor.parseRaw(
                            replaceLine(
                                    lines,
                                    1,
                                    first.replace(
                                            mutation.getKey(),
                                            mutation.getValue())),
                            filename(scenario),
                            scenario.batchId()));
            assertEquals("INVALID_FIELD", exception.code());
        }
    }

    @Test
    void descriptionsEnforceCodepointsControlsBidiFormulaAndDigitRuns()
            throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] valid = fixtureBytes(scenario.source());
        List<String> lines = lines(valid);
        String first = lines.get(1);
        for (String unsafe : List.of(
                "=FORMULA",
                "+FORMULA",
                "-FORMULA",
                "@FORMULA",
                "control\u0001text",
                "bidi\u202etext",
                "digits 12345678901",
                "CNPJ 12345678000195",
                "A".repeat(81))) {
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type05Processor.parseRaw(
                            singleRow(
                                    lines,
                                    description(first, unsafe)),
                            filename(scenario),
                            scenario.batchId()));
            assertEquals("INVALID_DESCRIPTION", exception.code(), unsafe);
        }

        String eightySupplementary = "\ud83d\udcb3".repeat(80);
        Type05Processor.ParsedBatch codePointBoundary =
                Type05Processor.parseRaw(
                        singleRow(
                                lines,
                                description(
                                        first,
                                        eightySupplementary)),
                        filename(scenario),
                        scenario.batchId());
        assertEquals(
                80,
                codePointBoundary.assessments().getFirst()
                        .description().codePointCount(
                                0,
                                codePointBoundary.assessments().getFirst()
                                        .description().length()));

        String byteHeavyDescription = "\ud83d\udcb3".repeat(120);
        byte[] byteOversized = singleRow(
                lines,
                description(first, byteHeavyDescription));
        String oversizedLine = lines(byteOversized).get(1);
        assertTrue(
                oversizedLine.getBytes(StandardCharsets.UTF_8).length
                        > 512);
        assertTrue(oversizedLine.length() < 512);
        ProcessorException recordLength = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.parseRaw(
                        byteOversized,
                        filename(scenario),
                        scenario.batchId()));
        assertEquals("INVALID_RECORD_LENGTH", recordLength.code());
    }

    @Test
    void calculatedZeroAndAggregateAboveSingleRowCeilingAreValid()
            throws Exception {
        Scenario minimal = acceptedScenarios().getFirst();
        List<String> minimalLines = lines(
                fixtureBytes(minimal.source()));
        String zeroRow = minimalLines.get(1).replace(
                "1000,00;1,235;12,35",
                "0,01;0,001;0,00");
        Type05Processor.ParsedBatch zero =
                Type05Processor.parseRaw(
                        singleRow(minimalLines, zeroRow),
                        filename(minimal),
                        minimal.batchId());
        assertEquals(
                "0.00",
                money(zero.assessments().getFirst().calculatedFee()));

        Scenario boundary = acceptedScenarios().get(1);
        List<String> boundaryLines = lines(
                fixtureBytes(boundary.source()));
        String duplicate = boundaryLines.get(1)
                .replace(
                        "FEE2000022904003",
                        "FEE2000022904004")
                .replace(
                        "MER9999999999999",
                        "MER9999999999998");
        byte[] twoRows = join(List.of(
                boundaryLines.get(0),
                boundaryLines.get(1),
                duplicate));
        Type05Processor.ParsedBatch aggregated =
                Type05Processor.parseRaw(
                        twoRows,
                        filename(boundary),
                        boundary.batchId());
        assertEquals(
                "1999999999999.98",
                money(aggregated.computedGrossAmount()));
        JsonNode aggregateManifest = manifest(
                new Scenario(
                        boundary.source(),
                        boundary.expectedCsv(),
                        boundary.fileDate(),
                        boundary.batchId(),
                        2,
                        "1999999999999.98",
                        "1999999999999.98",
                        "1999999999999.98",
                        null),
                twoRows);
        Type05Processor.validateSourceControls(
                aggregated,
                aggregateManifest);
    }

    @Test
    void manifestDispatcherPublishesCanonicalBundleManifestLast(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] raw = fixtureBytes(scenario.source());
        byte[] manifestBytes = StableJson.bytes(
                manifestMap(scenario, raw));
        String directory = "/raw/processing/" + scenario.batchId();
        String sourceFilename = filename(scenario);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of(
                directory + "/source-manifest.json",
                manifestBytes,
                directory + "/" + sourceFilename,
                raw,
                directory + "/" + sourceFilename + ".sha256",
                (ArtifactIO.sha256(raw)
                        + "  "
                        + sourceFilename
                        + "\n").getBytes(StandardCharsets.US_ASCII)));

        ProcessorResult result = new ProcessorDispatcher(
                List.of(new Type05Processor())).dispatch(
                        scenario.batchId(),
                        "05",
                        configuration(),
                        gateway,
                        workingDirectory);

        assertEquals("succeeded", result.asMap().get("status"));
        assertEquals(
                scenario.csvSha256(),
                result.asMap().get("csv_sha256"));
        assertEquals(2, result.asMap().get("row_count"));
        assertEquals("1001.00", result.asMap().get("gross_amount"));
        assertEquals("12.36", result.asMap().get("assessed_fee"));
        assertEquals("12.36", result.asMap().get("calculated_fee"));
        String sanitizedFilename = sourceFilename.replace(
                ".csv",
                "_SANITIZED.csv");
        assertEquals(
                List.of(
                        sanitizedFilename,
                        sanitizedFilename + ".sha256",
                        "sanitized-manifest.json"),
                gateway.published.keySet().stream().toList());
        assertEquals(
                "sanitized-manifest.json",
                gateway.readinessManifest);
        assertArrayEquals(
                fixtureBytes(scenario.expectedCsv()),
                gateway.published.get(sanitizedFilename));
        JsonNode sanitized = StableJson.parse(
                gateway.published.get("sanitized-manifest.json"));
        assertEquals(
                "05",
                sanitized.path("file_type").path("number").asText());
        assertEquals(
                "NFC",
                sanitized.path("csv_file")
                        .path("unicode_normalization").asText());
        assertEquals(
                "12.36",
                sanitized.path("stage_controls")
                        .path("calculated_fee").asText());
    }

    @Test
    void controlAndPrivacyFailuresPublishNoPartialArtifacts(
            @TempDir Path workingDirectory) throws Exception {
        Scenario darkFactory = darkFactoryScenario();
        byte[] darkRaw = fixtureBytes(darkFactory.source());
        FakeArtifactGateway controlGateway =
                new FakeArtifactGateway(Map.of());
        ProcessorException control = assertThrows(
                ProcessorException.class,
                () -> new Type05Processor().process(context(
                        darkFactory,
                        darkRaw,
                        manifest(darkFactory, darkRaw),
                        controlGateway,
                        workingDirectory)));
        assertEquals(
                "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
                control.code());
        assertNoOutput(controlGateway, workingDirectory, darkFactory);

        Scenario minimal = acceptedScenarios().getFirst();
        byte[] collisionRaw = text(
                fixtureBytes(minimal.source()))
                .replace(
                        minimal.batchId(),
                        "B012345678000195")
                .getBytes(StandardCharsets.UTF_8);
        Scenario collision = new Scenario(
                minimal.source(),
                null,
                minimal.fileDate(),
                "B012345678000195",
                minimal.rowCount(),
                minimal.gross(),
                minimal.assessed(),
                minimal.calculated(),
                null);
        FakeArtifactGateway privacyGateway =
                new FakeArtifactGateway(Map.of());
        ProcessorException privacy = assertThrows(
                ProcessorException.class,
                () -> new Type05Processor().process(context(
                        collision,
                        collisionRaw,
                        manifest(collision, collisionRaw),
                        privacyGateway,
                        workingDirectory)));
        assertEquals("PRIVACY_OUTPUT_VIOLATION", privacy.code());
        assertNoOutput(privacyGateway, workingDirectory, collision);
        String evidence = StableJson.line(
                ProcessorResult.rejected(
                        collision.batchId(),
                        "05",
                        privacy).asMap());
        assertFalse(evidence.contains("12345678000195"));
        assertFalse(evidence.contains("**********0195"));
    }

    @Test
    void exactManifestShapeAndNoNewSecretFailClosedCorrectly(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] raw = fixtureBytes(scenario.source());
        ObjectNode extra = manifest(scenario, raw).deepCopy();
        extra.put("unexpected", true);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());
        ProcessorException invalid = assertThrows(
                ProcessorException.class,
                () -> new Type05Processor().process(context(
                        scenario,
                        raw,
                        extra,
                        gateway,
                        workingDirectory)));
        assertEquals("INVALID_MANIFEST", invalid.code());
        assertTrue(gateway.published.isEmpty());

        ObjectNode hugeInteger = manifest(scenario, raw).deepCopy();
        hugeInteger.put("schema_version", 4_294_967_297L);
        ProcessorException huge = assertThrows(
                ProcessorException.class,
                () -> new Type05Processor().process(context(
                        scenario,
                        raw,
                        hugeInteger,
                        gateway,
                        workingDirectory)));
        assertEquals("INVALID_MANIFEST", huge.code());

        ProcessorResult success = new Type05Processor().process(context(
                scenario,
                raw,
                manifest(scenario, raw),
                gateway,
                workingDirectory));
        assertEquals("succeeded", success.asMap().get("status"));
        assertNull(configuration().tokenizationKey());
        assertNull(configuration().documentTokenKey());
        assertNull(configuration().tedAccountTokenKey());
    }

    private static void assertNoOutput(
            FakeArtifactGateway gateway,
            Path workingDirectory,
            Scenario scenario) {
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(workingDirectory.resolve(
                filename(scenario).replace(
                        ".csv",
                        "_SANITIZED.csv"))));
        assertFalse(Files.exists(workingDirectory.resolve(
                "sanitized-manifest.json")));
    }

    private static void assertControlCode(
            Type05Processor.ParsedBatch parsed,
            JsonNode manifest,
            String expectedCode) {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type05Processor.validateSourceControls(
                        parsed,
                        manifest));
        assertEquals(expectedCode, exception.code());
    }

    private static ProcessingContext context(
            Scenario scenario,
            byte[] raw,
            JsonNode manifest,
            ArtifactGateway gateway,
            Path workingDirectory) throws ProcessorException {
        byte[] manifestBytes = StableJson.bytes(manifest);
        return new ProcessingContext(
                scenario.batchId(),
                configuration(),
                gateway,
                workingDirectory,
                manifestBytes,
                manifest,
                new ProcessingContext.SourceArtifact(
                        filename(scenario),
                        ArtifactIO.sha256(raw),
                        raw.length,
                        raw));
    }

    private static Configuration configuration() {
        return new Configuration(
                "unused",
                22,
                "unused",
                "unused",
                Path.of("unused"),
                null,
                null,
                null,
                null,
                null,
                null);
    }

    private static JsonNode manifest(
            Scenario scenario,
            byte[] raw) throws ProcessorException {
        return StableJson.parse(StableJson.bytes(
                manifestMap(scenario, raw)));
    }

    private static Map<String, Object> manifestMap(
            Scenario scenario,
            byte[] raw) {
        return Map.of(
                "batch_id", scenario.batchId(),
                "file_type", Map.of(
                        "code", "MER_FEESET05",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "05"),
                "schema_version", 1,
                "source_controls", Map.of(
                        "assessed_fee", scenario.assessed(),
                        "calculated_fee", scenario.calculated(),
                        "currency", "BRL",
                        "gross_amount", scenario.gross(),
                        "row_count", scenario.rowCount()),
                "source_file", Map.of(
                        "encoding", "UTF-8",
                        "final_newline", "required",
                        "line_ending", "LF",
                        "name", filename(scenario),
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length,
                        "unicode_normalization", "NFC"));
    }

    private static byte[] singleRow(
            List<String> lines,
            String firstRow) {
        return join(List.of(lines.getFirst(), firstRow));
    }

    private static String description(
            String row,
            String value) {
        String start = ";\"Tarifa \"\"VIP\"\"; julho, lote A\";";
        String escaped = value.replace("\"", "\"\"");
        return row.replace(start, ";\"" + escaped + "\";");
    }

    private static byte[] replaceLine(
            List<String> lines,
            int index,
            String replacement) {
        List<String> changed = new ArrayList<>(lines);
        changed.set(index, replacement);
        return join(changed);
    }

    private static byte[] join(List<String> lines) {
        return (String.join("\n", lines) + "\n")
                .getBytes(StandardCharsets.UTF_8);
    }

    private static List<String> lines(byte[] raw) {
        String value = text(raw);
        return List.of(value.substring(
                0,
                value.length() - 1).split("\\n", -1));
    }

    private static String text(byte[] raw) {
        return new String(raw, StandardCharsets.UTF_8);
    }

    private static String money(java.math.BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static List<Scenario> acceptedScenarios() {
        return List.of(
                new Scenario(
                        "valid-minimal.csv",
                        "expected-sanitized.csv",
                        "20260723",
                        "B202607230000401",
                        2,
                        "1001.00",
                        "12.36",
                        "12.36",
                        "cc13c6fa4ea028b7b7cbfaaf5b755a09cd8edcc424739515429388bd15978c48"),
                new Scenario(
                        "valid-boundary.csv",
                        "expected-valid-boundary-sanitized.csv",
                        "20000229",
                        "B200002290000402",
                        1,
                        "999999999999.99",
                        "999999999999.99",
                        "999999999999.99",
                        "3652ce3371208e45e1eef0c2f690599429d45a12bcea926af8898405532e480e"),
                new Scenario(
                        "rounding-half-up.csv",
                        "expected-rounding-half-up-sanitized.csv",
                        "20260723",
                        "B202607230000404",
                        2,
                        "3.50",
                        "0.04",
                        "0.04",
                        "29440b6691950b4333b2c96187a794e0916bfda07500ad8584ce2c165fc33c85"));
    }

    private static Scenario malformedScenario() {
        return new Scenario(
                "malformed.csv",
                null,
                "20260723",
                "B202607230000403",
                1,
                "10.00",
                "0.10",
                "0.10",
                null);
    }

    private static Scenario darkFactoryScenario() {
        return new Scenario(
                "df-source-005.csv",
                null,
                "20260723",
                "B202607230000405",
                1,
                "100.00",
                "0.99",
                "1.00",
                null);
    }

    private static String filename(Scenario scenario) {
        return "NW_MERCHANT_FEES_"
                + scenario.fileDate()
                + "_"
                + scenario.batchId()
                + ".csv";
    }

    private static byte[] fixtureBytes(String filename)
            throws java.io.IOException {
        return Files.readAllBytes(fixtureRoot().resolve(filename));
    }

    private static Path fixtureRoot() {
        return Path.of(System.getProperty(
                "contract.type05.fixture.root",
                "../../contracts/types/05-merchant-fee-assessment/main"))
                .toAbsolutePath()
                .normalize();
    }

    private record Scenario(
            String source,
            String expectedCsv,
            String fileDate,
            String batchId,
            int rowCount,
            String gross,
            String assessed,
            String calculated,
            String csvSha256) {
    }

    private static final class FakeArtifactGateway
            implements ArtifactGateway {
        private final Map<String, byte[]> downloads;
        private final LinkedHashMap<String, byte[]> published =
                new LinkedHashMap<>();
        private String readinessManifest;

        private FakeArtifactGateway(Map<String, byte[]> downloads) {
            this.downloads = Map.copyOf(downloads);
        }

        @Override
        public void download(String remotePath, Path localPath)
                throws ProcessorException {
            byte[] content = downloads.get(remotePath);
            if (content == null) {
                throw new ProcessorException(
                        "SFTP_DOWNLOAD_ERROR",
                        "Missing fake Type 05 source artifact");
            }
            try {
                Files.write(localPath, content);
            } catch (java.io.IOException exception) {
                throw new ProcessorException(
                        "LOCAL_IO_ERROR",
                        "Cannot write fake Type 05 artifact",
                        exception);
            }
        }

        @Override
        public void publish(
                String remoteDirectory,
                LinkedHashMap<String, Path> artifacts,
                String readiness) throws ProcessorException {
            readinessManifest = readiness;
            try {
                for (Map.Entry<String, Path> artifact
                        : artifacts.entrySet()) {
                    published.put(
                            artifact.getKey(),
                            Files.readAllBytes(artifact.getValue()));
                }
            } catch (java.io.IOException exception) {
                throw new ProcessorException(
                        "LOCAL_IO_ERROR",
                        "Cannot read fake Type 05 publication",
                        exception);
            }
        }

        @Override
        public void close() {
            // Deterministic in-memory gateway owns no external resources.
        }
    }
}
