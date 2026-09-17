package com.northwindpay.legacy.type03;

import com.fasterxml.jackson.databind.JsonNode;
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
import java.util.Arrays;
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
 * Contract vectors and adversarial boundary checks for Type 03.
 */
class Type03ProcessorTest {
    private static final String PAYMENT_KEY =
            "northwind-pay-edp-fixture-payment-reference-key-v1";
    private static final String PARTY_KEY =
            "northwind-pay-edp-fixture-party-key-v1";
    private static final String ACCOUNT_KEY =
            "northwind-pay-edp-fixture-account-key-v1";
    private static final String GENERIC_KEY =
            "northwind-pay-edp-fixture-key-v1";
    private static final String DOCUMENT_KEY =
            "northwind-pay-edp-fixture-document-key-v1";
    private static final Type03Processor.TokenKeys TOKEN_KEYS =
            new Type03Processor.TokenKeys(
                    PAYMENT_KEY,
                    PARTY_KEY,
                    ACCOUNT_KEY);

    @Test
    void canonicalAcceptedScenariosMatchApprovedCsvBytesAndHashes()
            throws Exception {
        List<Scenario> scenarios = List.of(
                new Scenario(
                        "valid-minimal.rem",
                        "expected-sanitized.csv",
                        "B202607230000201",
                        1,
                        8,
                        2,
                        "200.00",
                        "5.00",
                        "3.50",
                        "198.50",
                        "a108607f7d32017a954efce8ee35124d42429bb7a85a38ef58f700087fd4b941"),
                new Scenario(
                        "valid-boundary.rem",
                        "expected-valid-boundary-sanitized.csv",
                        "B202402290000202",
                        1,
                        6,
                        1,
                        "9999999999999.99",
                        "9999999999.99",
                        "9999999999.99",
                        "9999999999999.99",
                        "c5dc9621dee5f713a0634fcfdf69645b4e5d9515a529c0c6823eff6636a9bfcf"),
                new Scenario(
                        "multi-lot.rem",
                        "expected-multi-lot-sanitized.csv",
                        "B202607230000204",
                        2,
                        10,
                        2,
                        "200.00",
                        "5.00",
                        "3.50",
                        "198.50",
                        "31436cd3b718207452154e8a1d3f77e0d705e9721547582da056d1db632ca24f"));

        for (Scenario scenario : scenarios) {
            byte[] raw = fixtureBytes(scenario.source());
            String filename = filename(scenario.batchId());
            Type03Processor.ParsedBatch parsed =
                    Type03Processor.parseRaw(
                            raw,
                            filename,
                            scenario.batchId());
            Type03Processor.validateSourceControls(
                    parsed,
                    manifest(scenario, raw));
            Type03Processor.CsvOutput output =
                    Type03Processor.renderCsv(
                            parsed,
                            filename,
                            TOKEN_KEYS);

            assertArrayEquals(
                    fixtureBytes(scenario.expectedCsv()),
                    output.bytes(),
                    scenario.source());
            assertEquals(
                    scenario.csvSha256(),
                    ArtifactIO.sha256(output.bytes()),
                    scenario.source());
            assertEquals(scenario.logicalCount(), output.rowCount());
            assertEquals(0, output.orphanSegmentCount());
        }
    }

    @Test
    void malformedPairAndDarkFactoryFindingMatchCanonicalEvidence()
            throws Exception {
        ProcessorException malformed = assertThrows(
                ProcessorException.class,
                () -> Type03Processor.parseRaw(
                        fixtureBytes("malformed.rem"),
                        filename("B202607230000203"),
                        "B202607230000203"));
        assertEquals("SEGMENT_PAIR_MISMATCH", malformed.code());
        assertEquals(4, malformed.recordNumber());

        Scenario darkFactory = new Scenario(
                "df-source-003.rem",
                null,
                "B202607230000205",
                1,
                8,
                2,
                "200.00",
                "5.00",
                "3.50",
                "198.49",
                null);
        byte[] raw = fixtureBytes(darkFactory.source());
        Type03Processor.ParsedBatch parsed =
                Type03Processor.parseRaw(
                        raw,
                        filename(darkFactory.batchId()),
                        darkFactory.batchId());
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type03Processor.validateSourceControls(
                        parsed,
                        manifest(darkFactory, raw)));
        assertEquals("SOURCE_CONTROL_NET_MISMATCH", exception.code());
        assertEquals(1, exception.declaredLotCount());
        assertEquals(1, exception.computedLotCount());
        assertEquals(8, exception.declaredPhysicalRecordCount());
        assertEquals(8, exception.computedPhysicalRecordCount());
        assertEquals(2, exception.declaredLogicalCount());
        assertEquals(2, exception.computedLogicalCount());
        assertEquals("200.00", exception.declaredFaceAmount());
        assertEquals("200.00", exception.computedFaceAmount());
        assertEquals("5.00", exception.declaredDiscountAmount());
        assertEquals("5.00", exception.computedDiscountAmount());
        assertEquals("3.50", exception.declaredFeeAmount());
        assertEquals("3.50", exception.computedFeeAmount());
        assertEquals("198.49", exception.declaredNetAmount());
        assertEquals("198.50", exception.computedNetAmount());
        assertEquals(0, exception.computedOrphanSegmentCount());

        Map<String, Object> rejection = ProcessorResult.rejected(
                darkFactory.batchId(),
                "03",
                exception).asMap();
        assertEquals("rejected", rejection.get("status"));
        assertEquals(
                "SOURCE_CONTROL_NET_MISMATCH",
                rejection.get("code"));
        assertEquals("198.49", rejection.get("declared_net_amount"));
        assertEquals("198.50", rejection.get("computed_net_amount"));
        assertEquals(
                0,
                rejection.get("computed_orphan_segment_count"));
        assertFalse(rejection.containsKey("transaction_id"));
        assertFalse(rejection.containsKey("detail_amounts"));
    }

    @Test
    void declaredValidationPrecedenceIsGlobal() throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.rem");
        String batchId = "B202607230000201";
        String filename = filename(batchId);

        byte[] invalidAscii = mutate(valid, 4, 30, "X");
        invalidAscii[0] = (byte) 0x80;
        assertParseCode(
                invalidAscii,
                filename,
                batchId,
                "INVALID_ASCII");

        byte[] invalidTransport = Arrays.copyOf(
                valid,
                valid.length - 1);
        invalidTransport[0] = 'X';
        assertParseCode(
                invalidTransport,
                filename,
                batchId,
                "INVALID_TRANSPORT");

        byte[] shortRecord = new byte[valid.length - 1];
        System.arraycopy(valid, 0, shortRecord, 0, 239);
        System.arraycopy(
                valid,
                240,
                shortRecord,
                239,
                valid.length - 240);
        shortRecord[242] = 'X';
        assertParseCode(
                shortRecord,
                filename,
                batchId,
                "INVALID_RECORD_LENGTH");

        byte[] grammarBeforeStatic = mutate(valid, 2, 0, "X");
        grammarBeforeStatic = mutate(
                grammarBeforeStatic,
                1,
                54,
                "!");
        assertParseCode(
                grammarBeforeStatic,
                filename,
                batchId,
                "INVALID_RECORD_SEQUENCE");

        byte[] fillerBeforeLexical = mutate(valid, 1, 54, "!");
        fillerBeforeLexical = mutate(
                fillerBeforeLexical,
                3,
                29,
                "X");
        assertParseCode(
                fillerBeforeLexical,
                filename,
                batchId,
                "INVALID_FILLER");

        byte[] lexicalBeforeDocument = mutate(
                valid,
                3,
                29,
                "X");
        lexicalBeforeDocument = mutate(
                lexicalBeforeDocument,
                4,
                30,
                "00011111111111");
        assertParseCode(
                lexicalBeforeDocument,
                filename,
                batchId,
                "INVALID_FIELD");

        byte[] documentBeforeIdentifier = mutate(
                valid,
                4,
                30,
                "00011111111111");
        documentBeforeIdentifier = mutate(
                documentBeforeIdentifier,
                3,
                13,
                "0");
        assertParseCode(
                documentBeforeIdentifier,
                filename,
                batchId,
                "INVALID_DOCUMENT");

        byte[] identifierBeforePairing = mutate(valid, 3, 13, "0");
        identifierBeforePairing = mutate(
                identifierBeforePairing,
                4,
                7,
                "000009");
        assertParseCode(
                identifierBeforePairing,
                filename,
                batchId,
                "INVALID_IDENTIFIER");
    }

    @Test
    void blankRecordsAreTransportFailuresBeforeGrammar()
            throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.rem");
        byte[] withBlank = new byte[valid.length + 2];
        System.arraycopy(valid, 0, withBlank, 0, 242);
        withBlank[242] = '\r';
        withBlank[243] = '\n';
        System.arraycopy(
                valid,
                242,
                withBlank,
                244,
                valid.length - 242);

        assertParseCode(
                withBlank,
                filename("B202607230000201"),
                "B202607230000201",
                "INVALID_TRANSPORT");
    }

    @Test
    void logicalRowLimitFailsAsSourceSizeBeforeFieldParsing()
            throws Exception {
        String[] records = new String(
                fixtureBytes("valid-minimal.rem"),
                StandardCharsets.US_ASCII)
                .substring(0, 8 * 242 - 2)
                .split("\\r\\n");
        StringBuilder oversized = new StringBuilder(20_005 * 242);
        oversized.append(records[0]).append("\r\n");
        oversized.append(records[1]).append("\r\n");
        for (int index = 0; index < 10_001; index++) {
            oversized.append(records[2]).append("\r\n");
            oversized.append(records[3]).append("\r\n");
        }
        oversized.append(records[6]).append("\r\n");
        oversized.append(records[7]).append("\r\n");

        assertParseCode(
                oversized.toString().getBytes(
                        StandardCharsets.US_ASCII),
                filename("B202607230000201"),
                "B202607230000201",
                "INVALID_SOURCE_SIZE");
    }

    @Test
    void nonOutputOriginatorMayEqualRestrictedBeneficiaryName()
            throws Exception {
        String originator = "NWPORIGIN0000001";
        byte[] raw = mutate(
                fixtureBytes("valid-minimal.rem"),
                4,
                44,
                originator + " ".repeat(40 - originator.length()));

        Type03Processor.ParsedBatch parsed =
                Type03Processor.parseRaw(
                        raw,
                        filename("B202607230000201"),
                        "B202607230000201");
        Type03Processor.CsvOutput output =
                Type03Processor.renderCsv(
                        parsed,
                        filename("B202607230000201"),
                        TOKEN_KEYS);

        assertEquals(2, output.rowCount());
        assertFalse(new String(
                output.bytes(),
                StandardCharsets.UTF_8).contains(originator));
    }

    @Test
    void manifestDeclarationsAreCheckedBeforeComputedControls()
            throws Exception {
        Scenario darkFactory = new Scenario(
                "df-source-003.rem",
                null,
                "B202607230000205",
                1,
                8,
                2,
                "200.00",
                "5.00",
                "3.50",
                "198.50",
                null);
        byte[] raw = fixtureBytes(darkFactory.source());
        Type03Processor.ParsedBatch parsed =
                Type03Processor.parseRaw(
                        raw,
                        filename(darkFactory.batchId()),
                        darkFactory.batchId());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type03Processor.validateSourceControls(
                        parsed,
                        manifest(darkFactory, raw)));

        assertEquals("INVALID_MANIFEST", exception.code());
        assertNull(exception.declaredNetAmount());
    }

    @Test
    void privacySafeFailureNeverSerializesRawRestrictedValues()
            throws Exception {
        String restrictedDocument = "00011111111111";
        byte[] raw = mutate(
                fixtureBytes("valid-minimal.rem"),
                4,
                30,
                restrictedDocument);
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type03Processor.parseRaw(
                        raw,
                        filename("B202607230000201"),
                        "B202607230000201"));
        String evidence = StableJson.line(
                ProcessorResult.rejected(
                        "B202607230000201",
                        "03",
                        exception).asMap());

        assertEquals("INVALID_DOCUMENT", exception.code());
        assertFalse(evidence.contains(restrictedDocument));
        assertFalse(evidence.contains("11111111111"));
        assertFalse(evidence.contains("party_"));
        assertFalse(evidence.contains("acct_"));
        assertFalse(evidence.contains("payref_"));
    }

    @Test
    void missingOrReusedTokenDomainsFailClosedWithoutPublication(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = minimalScenario();
        byte[] raw = fixtureBytes(scenario.source());
        JsonNode manifest = manifest(scenario, raw);

        Configuration missing = configuration(null, PARTY_KEY, ACCOUNT_KEY);
        FakeArtifactGateway missingGateway = new FakeArtifactGateway(Map.of());
        ProcessorException missingFailure = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        missing,
                        missingGateway,
                        workingDirectory)));
        assertEquals("TOKENIZATION_KEY_MISSING", missingFailure.code());
        assertTrue(missingGateway.published.isEmpty());

        Configuration equalDomains =
                configuration(PAYMENT_KEY, PAYMENT_KEY, ACCOUNT_KEY);
        FakeArtifactGateway equalGateway = new FakeArtifactGateway(Map.of());
        ProcessorException equalFailure = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        equalDomains,
                        equalGateway,
                        workingDirectory)));
        assertEquals("TOKENIZATION_KEY_REUSE", equalFailure.code());
        assertTrue(equalGateway.published.isEmpty());

        Configuration genericReuse =
                configuration(GENERIC_KEY, PARTY_KEY, ACCOUNT_KEY);
        FakeArtifactGateway genericGateway =
                new FakeArtifactGateway(Map.of());
        ProcessorException genericFailure = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        genericReuse,
                        genericGateway,
                        workingDirectory)));
        assertEquals("TOKENIZATION_KEY_REUSE", genericFailure.code());
        assertTrue(genericGateway.published.isEmpty());

        Configuration documentReuse =
                configuration(DOCUMENT_KEY, PARTY_KEY, ACCOUNT_KEY);
        FakeArtifactGateway documentGateway =
                new FakeArtifactGateway(Map.of());
        ProcessorException documentFailure = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        documentReuse,
                        documentGateway,
                        workingDirectory)));
        assertEquals("TOKENIZATION_KEY_REUSE", documentFailure.code());
        assertTrue(documentGateway.published.isEmpty());
    }

    @Test
    void oversizedJsonIntegersCannotTruncateIntoManifestConstants(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = minimalScenario();
        byte[] raw = fixtureBytes(scenario.source());
        JsonNode invalid = manifest(scenario, raw);
        ((com.fasterxml.jackson.databind.node.ObjectNode) invalid)
                .put("schema_version", 4_294_967_297L);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        invalid,
                        configuration(
                                PAYMENT_KEY,
                                PARTY_KEY,
                                ACCOUNT_KEY),
                        gateway,
                        workingDirectory)));

        assertEquals("INVALID_MANIFEST", exception.code());
        assertTrue(gateway.published.isEmpty());
    }

    @Test
    void environmentLoadsAllType03KeysWithoutSerializingThem()
            throws Exception {
        Configuration configuration = Configuration.fromEnvironment(
                Map.of(
                        "SFTP_HOST", "sftp",
                        "SFTP_PORT", "22",
                        "SFTP_PROCESSOR_USER", "processor",
                        "SFTP_PROCESSOR_PASSWORD", "password",
                        "SFTP_KNOWN_HOSTS", "/known_hosts",
                        "NWP_TOKENIZATION_KEY", GENERIC_KEY,
                        "NWP_DOCUMENT_TOKEN_KEY", DOCUMENT_KEY,
                        "NWP_PAYMENT_REFERENCE_KEY", PAYMENT_KEY,
                        "NWP_PARTY_TOKEN_KEY", PARTY_KEY,
                        "NWP_ACCOUNT_TOKEN_KEY", ACCOUNT_KEY));

        assertEquals(
                PAYMENT_KEY,
                configuration.paymentReferenceKey());
        assertEquals(PARTY_KEY, configuration.partyTokenKey());
        assertEquals(ACCOUNT_KEY, configuration.accountTokenKey());
        String diagnostic = configuration.toString();
        assertFalse(diagnostic.contains(PAYMENT_KEY));
        assertFalse(diagnostic.contains(PARTY_KEY));
        assertFalse(diagnostic.contains(ACCOUNT_KEY));
    }

    @Test
    void manifestDispatcherPublishesCsvChecksumAndManifestLast(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = minimalScenario();
        byte[] raw = fixtureBytes(scenario.source());
        byte[] manifestBytes = StableJson.bytes(
                manifestMap(scenario, raw));
        String directory = "/raw/processing/" + scenario.batchId();
        String sourceFilename = filename(scenario.batchId());
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
                List.of(new Type03Processor())).dispatch(
                        scenario.batchId(),
                        "03",
                        configuration(PAYMENT_KEY, PARTY_KEY, ACCOUNT_KEY),
                        gateway,
                        workingDirectory);

        assertEquals("succeeded", result.asMap().get("status"));
        assertEquals(scenario.csvSha256(), result.asMap().get("csv_sha256"));
        assertEquals(2, result.asMap().get("row_count"));
        assertEquals("200.00", result.asMap().get("face_amount"));
        assertEquals("5.00", result.asMap().get("discount_amount"));
        assertEquals("3.50", result.asMap().get("fee_amount"));
        assertEquals("198.50", result.asMap().get("net_amount"));
        assertEquals(0, result.asMap().get("orphan_segment_count"));
        assertEquals(
                List.of(
                        sourceFilename.replace(".rem", ".csv"),
                        sourceFilename.replace(".rem", ".csv.sha256"),
                        "sanitized-manifest.json"),
                gateway.published.keySet().stream().toList());
        assertEquals(
                "sanitized-manifest.json",
                gateway.readinessManifest);
        assertArrayEquals(
                fixtureBytes(scenario.expectedCsv()),
                gateway.published.get(
                        sourceFilename.replace(".rem", ".csv")));
        JsonNode sanitized = StableJson.parse(
                gateway.published.get("sanitized-manifest.json"));
        assertEquals(
                "03",
                sanitized.path("file_type").path("number").asText());
        assertEquals(
                scenario.csvSha256(),
                sanitized.path("csv_file").path("sha256").asText());
        assertEquals(
                "198.50",
                sanitized.path("stage_controls").path(
                        "net_amount").asText());
    }

    @Test
    void rejectedBatchCreatesNoLocalOrPublishedSanitizedArtifact(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = new Scenario(
                "df-source-003.rem",
                null,
                "B202607230000205",
                1,
                8,
                2,
                "200.00",
                "5.00",
                "3.50",
                "198.49",
                null);
        byte[] raw = fixtureBytes(scenario.source());
        JsonNode manifest = manifest(scenario, raw);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        configuration(
                                PAYMENT_KEY,
                                PARTY_KEY,
                                ACCOUNT_KEY),
                        gateway,
                        workingDirectory)));

        assertEquals("SOURCE_CONTROL_NET_MISMATCH", exception.code());
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(workingDirectory.resolve(
                filename(scenario.batchId()).replace(".rem", ".csv"))));
        assertFalse(Files.exists(workingDirectory.resolve(
                "sanitized-manifest.json")));
    }

    @Test
    void wholeOutputCollisionRejectsBeforeAnyPublication(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = minimalScenario();
        String restrictedName = "SETTLED";
        byte[] raw = mutate(
                fixtureBytes(scenario.source()),
                4,
                44,
                restrictedName
                        + " ".repeat(40 - restrictedName.length()));
        JsonNode manifest = manifest(scenario, raw);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type03Processor().process(context(
                        scenario.batchId(),
                        raw,
                        manifest,
                        configuration(
                                PAYMENT_KEY,
                                PARTY_KEY,
                                ACCOUNT_KEY),
                        gateway,
                        workingDirectory)));
        String evidence = StableJson.line(
                ProcessorResult.rejected(
                        scenario.batchId(),
                        "03",
                        exception).asMap());

        assertEquals("PRIVACY_BOUNDARY_VIOLATION", exception.code());
        assertFalse(evidence.contains(restrictedName));
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(workingDirectory.resolve(
                filename(scenario.batchId()).replace(".rem", ".csv"))));
        assertFalse(Files.exists(workingDirectory.resolve(
                "sanitized-manifest.json")));
    }

    private static void assertParseCode(
            byte[] raw,
            String filename,
            String batchId,
            String expectedCode) {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type03Processor.parseRaw(
                        raw,
                        filename,
                        batchId));
        assertEquals(expectedCode, exception.code());
    }

    private static byte[] mutate(
            byte[] raw,
            int recordNumber,
            int zeroBasedStart,
            String replacement) {
        byte[] result = raw.clone();
        byte[] bytes = replacement.getBytes(StandardCharsets.US_ASCII);
        int offset = (recordNumber - 1) * 242 + zeroBasedStart;
        System.arraycopy(bytes, 0, result, offset, bytes.length);
        return result;
    }

    private static ProcessingContext context(
            String batchId,
            byte[] raw,
            JsonNode manifest,
            Configuration configuration,
            ArtifactGateway gateway,
            Path workingDirectory) throws ProcessorException {
        byte[] manifestBytes = StableJson.bytes(manifest);
        return new ProcessingContext(
                batchId,
                configuration,
                gateway,
                workingDirectory,
                manifestBytes,
                manifest,
                new ProcessingContext.SourceArtifact(
                        filename(batchId),
                        ArtifactIO.sha256(raw),
                        raw.length,
                        raw));
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
                        "code", "PAYSLIPSET03",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "03"),
                "schema_version", 1,
                "source_controls", Map.of(
                        "currency", "BRL",
                        "discount_amount", scenario.discount(),
                        "face_amount", scenario.face(),
                        "fee_amount", scenario.fee(),
                        "logical_count", scenario.logicalCount(),
                        "lot_count", scenario.lotCount(),
                        "net_amount", scenario.net(),
                        "orphan_segment_count", 0,
                        "physical_record_count",
                        scenario.physicalCount()),
                "source_file", Map.of(
                        "encoding", "US-ASCII",
                        "final_newline", "required",
                        "line_ending", "CRLF",
                        "name", filename(scenario.batchId()),
                        "record_length_bytes", 240,
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length));
    }

    private static Configuration configuration(
            String paymentKey,
            String partyKey,
            String accountKey) {
        return new Configuration(
                "unused",
                22,
                "unused",
                "unused",
                Path.of("unused"),
                GENERIC_KEY,
                DOCUMENT_KEY,
                paymentKey,
                partyKey,
                accountKey);
    }

    private static Scenario minimalScenario() {
        return new Scenario(
                "valid-minimal.rem",
                "expected-sanitized.csv",
                "B202607230000201",
                1,
                8,
                2,
                "200.00",
                "5.00",
                "3.50",
                "198.50",
                "a108607f7d32017a954efce8ee35124d42429bb7a85a38ef58f700087fd4b941");
    }

    private static String filename(String batchId) {
        return "NW_PAYMENT_SLIP_"
                + batchId.substring(1, 9)
                + "_"
                + batchId
                + ".rem";
    }

    private static byte[] fixtureBytes(String filename)
            throws java.io.IOException {
        return Files.readAllBytes(fixtureRoot().resolve(filename));
    }

    private static Path fixtureRoot() {
        return Path.of(System.getProperty(
                "contract.type03.fixture.root",
                "../../contracts/types/03-payment-slip-settlement/main"))
                .toAbsolutePath()
                .normalize();
    }

    private record Scenario(
            String source,
            String expectedCsv,
            String batchId,
            int lotCount,
            int physicalCount,
            int logicalCount,
            String face,
            String discount,
            String fee,
            String net,
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
                        "Missing fake source artifact");
            }
            try {
                Files.write(localPath, content);
            } catch (java.io.IOException exception) {
                throw new ProcessorException(
                        "LOCAL_IO_ERROR",
                        "Cannot write fake source artifact",
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
                        "Cannot read fake sanitized artifact",
                        exception);
            }
        }

        @Override
        public void close() {
            // No remote resources.
        }
    }
}
