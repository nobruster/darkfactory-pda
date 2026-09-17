package com.northwindpay.legacy.type04;

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

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
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
 * Canonical vectors and adversarial trust-boundary checks for Type 04.
 */
class Type04ProcessorTest {
    private static final String GENERIC_KEY =
            "northwind-pay-edp-fixture-key-v1";
    private static final String DOCUMENT_KEY =
            "northwind-pay-edp-fixture-document-key-v1";
    private static final String PAYMENT_KEY =
            "northwind-pay-edp-fixture-payment-reference-key-v1";
    private static final String PARTY_KEY =
            "northwind-pay-edp-fixture-party-key-v1";
    private static final String ACCOUNT_KEY =
            "northwind-pay-edp-fixture-account-key-v1";
    private static final String TED_KEY =
            "northwind-pay-edp-fixture-ted-account-key-v1";
    private static final Type04Processor.TokenKey TOKEN_KEY =
            new Type04Processor.TokenKey(TED_KEY);

    @Test
    void canonicalAcceptedScenariosMatchApprovedCsvBytesAndHashes()
            throws Exception {
        for (Scenario scenario : acceptedScenarios()) {
            byte[] raw = fixtureBytes(scenario.source());
            String filename = filename(scenario.batchId());
            Type04Processor.ParsedBatch parsed =
                    Type04Processor.parseRaw(
                            raw,
                            filename,
                            scenario.batchId());
            Type04Processor.validateSourceControls(
                    parsed,
                    manifest(scenario, raw));
            Type04Processor.CsvOutput output =
                    Type04Processor.renderCsv(
                            parsed,
                            filename,
                            TOKEN_KEY);

            assertArrayEquals(
                    fixtureBytes(scenario.expectedCsv()),
                    output.bytes(),
                    scenario.source());
            assertEquals(
                    scenario.csvSha256(),
                    ArtifactIO.sha256(output.bytes()),
                    scenario.source());
            assertEquals(scenario.transferCount(), output.transferCount());
            assertEquals(scenario.returnCount(), output.returnCount());
            assertEquals(
                    scenario.transferCount() + scenario.returnCount(),
                    output.rowCount());
            assertEquals(
                    scenario.grossAmount(),
                    output.grossAmount().toPlainString());
            assertEquals(
                    scenario.returnAmount(),
                    output.returnAmount().toPlainString());
            assertEquals(
                    scenario.netAmount(),
                    output.netAmount().toPlainString());
        }
    }

    @Test
    void malformedTransportAndDarkFactoryFindingMatchCanonicalEvidence()
            throws Exception {
        ProcessorException malformed = assertThrows(
                ProcessorException.class,
                () -> Type04Processor.parseRaw(
                        fixtureBytes("malformed.dat"),
                        filename("B202607230000303"),
                        "B202607230000303"));
        assertEquals("INVALID_TRANSPORT", malformed.code());
        assertNull(malformed.recordNumber());

        Scenario darkFactory = darkFactoryScenario();
        byte[] raw = fixtureBytes(darkFactory.source());
        Type04Processor.ParsedBatch parsed =
                Type04Processor.parseRaw(
                        raw,
                        filename(darkFactory.batchId()),
                        darkFactory.batchId());
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type04Processor.validateSourceControls(
                        parsed,
                        manifest(darkFactory, raw)));

        assertEquals("SOURCE_CONTROL_NET_MISMATCH", exception.code());
        assertEquals(2, exception.declaredTransferCount());
        assertEquals(2, exception.computedTransferCount());
        assertEquals(1, exception.declaredReturnCount());
        assertEquals(1, exception.computedReturnCount());
        assertEquals("1250.00", exception.declaredGrossAmount());
        assertEquals("1250.00", exception.computedGrossAmount());
        assertEquals("-250.00", exception.declaredReturnAmount());
        assertEquals("-250.00", exception.computedReturnAmount());
        assertEquals("999.99", exception.declaredNetAmount());
        assertEquals("1000.00", exception.computedNetAmount());

        Map<String, Object> result = ProcessorResult.rejected(
                darkFactory.batchId(),
                "04",
                exception).asMap();
        assertEquals("rejected", result.get("status"));
        assertEquals("999.99", result.get("declared_net_amount"));
        assertEquals("1000.00", result.get("computed_net_amount"));
        assertFalse(result.containsKey("transaction_id"));
        assertFalse(result.containsKey("detail_amounts"));
    }

    @Test
    void everyDeclaredRejectionPhaseHasExecutableCoverage()
            throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.dat");
        Map<String, byte[]> cases = new LinkedHashMap<>();

        cases.put(
                "INVALID_SOURCE_SIZE",
                new byte[2_570_143]);
        byte[] invalidAscii = valid.clone();
        invalidAscii[55] = (byte) 0xff;
        cases.put("INVALID_ASCII", invalidAscii);
        cases.put("INVALID_TRANSPORT", removeByte(valid, 56));

        List<byte[]> shortRecord = records(valid);
        shortRecord.set(
                1,
                Arrays.copyOf(shortRecord.get(1), 161));
        cases.put("INVALID_RECORD_LENGTH", join(shortRecord));
        cases.put(
                "INVALID_RECORD_SEQUENCE",
                mutate(valid, 2, 0, 1, "X"));
        cases.put(
                "INVALID_PADDING",
                mutate(valid, 3, 136, 137, "A"));
        cases.put(
                "INVALID_FIELD",
                mutate(valid, 2, 17, 18, "-"));
        cases.put(
                "INVALID_DOCUMENT",
                mutate(
                        valid,
                        2,
                        73,
                        87,
                        "99999999999999"));
        cases.put(
                "INVALID_IDENTIFIER",
                mutate(valid, 2, 1, 2, "1"));

        List<byte[]> missingReturn = records(valid);
        missingReturn.remove(3);
        cases.put("RETURN_LINK_MISMATCH", join(missingReturn));
        cases.put(
                "INVALID_TIMESTAMP",
                mutate(
                        valid,
                        4,
                        48,
                        62,
                        "20260723090000"));

        List<byte[]> duplicate = records(valid);
        byte[] secondTransfer = duplicate.get(2).clone();
        System.arraycopy(
                duplicate.get(1),
                1,
                secondTransfer,
                1,
                16);
        duplicate.set(2, secondTransfer);
        byte[] returned = duplicate.get(3).clone();
        System.arraycopy(
                duplicate.get(1),
                1,
                returned,
                17,
                16);
        duplicate.set(3, returned);
        cases.put("DUPLICATE_IDENTIFIER", join(duplicate));
        cases.put(
                "SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH",
                mutate(valid, 5, 9, 15, "000003"));
        cases.put(
                "SOURCE_CONTROL_RETURN_COUNT_MISMATCH",
                mutate(valid, 5, 15, 21, "000002"));
        cases.put(
                "SOURCE_CONTROL_GROSS_MISMATCH",
                mutate(valid, 5, 22, 36, "00000000125001"));
        cases.put(
                "SOURCE_CONTROL_RETURNED_MISMATCH",
                mutate(valid, 5, 37, 51, "00000000025001"));
        cases.put(
                "SOURCE_CONTROL_NET_MISMATCH",
                mutate(valid, 5, 52, 66, "00000000100001"));

        for (Map.Entry<String, byte[]> finding : cases.entrySet()) {
            assertContractCode(
                    finding.getValue(),
                    "B202607230000301",
                    finding.getKey());
        }

        byte[] documentThenIdentifier = mutate(
                mutate(
                        valid,
                        2,
                        1,
                        2,
                        "1"),
                2,
                73,
                87,
                "99999999999999");
        assertContractCode(
                documentThenIdentifier,
                "B202607230000301",
                "INVALID_DOCUMENT");

        byte[] paddingThenField = mutate(
                mutate(
                        valid,
                        3,
                        17,
                        18,
                        "-"),
                3,
                136,
                137,
                "A");
        assertContractCode(
                paddingThenField,
                "B202607230000301",
                "INVALID_PADDING");
    }

    @Test
    void conditionalGrammarPrecedesPoisonedTransferFields()
            throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.dat");
        List<byte[]> original = records(valid);
        byte[] poisonedRt = poisonTransfer(original.get(2));
        List<byte[]> missing = new ArrayList<>(original);
        missing.set(2, poisonedRt);
        missing.remove(3);

        byte[] poisonedOk = poisonTransfer(original.get(1));
        List<byte[]> extra = new ArrayList<>();
        extra.add(original.get(0));
        extra.add(poisonedOk);
        extra.add(original.get(3));
        extra.add(original.get(2));
        extra.add(original.get(3));
        extra.add(original.get(4));

        assertContractCode(
                join(missing),
                "B202607230000301",
                "RETURN_LINK_MISMATCH");
        assertContractCode(
                join(extra),
                "B202607230000301",
                "RETURN_LINK_MISMATCH");
    }

    @Test
    void returnFieldLinkageAndTimestampPrecedenceIsStable()
            throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.dat");
        List<byte[]> original = records(valid);

        byte[] badIdentifier = original.get(3).clone();
        badIdentifier[1] = '1';
        System.arraycopy(
                original.get(1),
                1,
                badIdentifier,
                17,
                16);
        List<byte[]> identifierRecords = new ArrayList<>(original);
        identifierRecords.set(3, badIdentifier);
        assertContractCode(
                join(identifierRecords),
                "B202607230000301",
                "INVALID_IDENTIFIER");

        byte[] badLinkAndTime = original.get(3).clone();
        System.arraycopy(
                original.get(1),
                1,
                badLinkAndTime,
                17,
                16);
        System.arraycopy(
                "20260723090000".getBytes(StandardCharsets.US_ASCII),
                0,
                badLinkAndTime,
                48,
                14);
        List<byte[]> linkRecords = new ArrayList<>(original);
        linkRecords.set(3, badLinkAndTime);
        assertContractCode(
                join(linkRecords),
                "B202607230000301",
                "RETURN_LINK_MISMATCH");
    }

    @Test
    void returnIdCannotEqualItsTransferId() throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.dat");
        List<byte[]> physical = records(valid);
        byte[] returned = physical.get(3).clone();
        System.arraycopy(
                physical.get(2),
                1,
                returned,
                1,
                16);
        physical.set(3, returned);

        assertContractCode(
                join(physical),
                "B202607230000301",
                "DUPLICATE_IDENTIFIER");
    }

    @Test
    void saoPauloGapIsRejectedAndCanonicalOffsetsIncludeSeconds()
            throws Exception {
        byte[] raw = fixtureBytes("valid-boundary.dat");
        Type04Processor.ParsedBatch boundary =
                Type04Processor.parseRaw(
                        raw,
                        filename("B200002290000302"),
                        "B200002290000302");
        byte[] rendered = Type04Processor.renderCsv(
                boundary,
                filename("B200002290000302"),
                TOKEN_KEY).bytes();
        assertTrue(new String(rendered, StandardCharsets.UTF_8)
                .contains("2000-02-29T23:59:59-03:00"));

        byte[] overlap = fixtureBytes("valid-boundary.dat");
        overlap = mutate(overlap, 1, 1, 9, "19900210");
        overlap = mutate(overlap, 1, 40, 48, "19900210");
        overlap = mutate(overlap, 2, 35, 49, "19900210233000");
        overlap = mutate(overlap, 3, 1, 9, "19900210");
        Type04Processor.ParsedBatch overlapBatch =
                Type04Processor.parseRaw(
                        overlap,
                        "NW_TED_SETTLEMENT_19900210_"
                                + "B200002290000302.dat",
                        "B200002290000302");
        String overlapCsv = new String(
                Type04Processor.renderCsv(
                        overlapBatch,
                        "NW_TED_SETTLEMENT_19900210_"
                                + "B200002290000302.dat",
                        TOKEN_KEY).bytes(),
                StandardCharsets.UTF_8);
        assertTrue(overlapCsv.contains(
                "1990-02-10T23:30:00-02:00"));

        byte[] gap = fixtureBytes("valid-minimal.dat");
        gap = mutate(gap, 1, 1, 9, "20181104");
        gap = mutate(gap, 1, 40, 48, "20181104");
        gap = mutate(gap, 2, 35, 49, "20181104003000");
        gap = mutate(gap, 3, 35, 43, "20181104");
        gap = mutate(gap, 5, 1, 9, "20181104");
        byte[] gapSource = gap;
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type04Processor.parseRaw(
                        gapSource,
                        "NW_TED_SETTLEMENT_20181104_"
                                + "B202607230000301.dat",
                        "B202607230000301"));
        assertEquals("INVALID_TIMESTAMP", exception.code());
        assertEquals(2, exception.recordNumber());
    }

    @Test
    void dedicatedKeyIsRequiredAndCannotReuseAnyEarlierDomain(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] raw = fixtureBytes(scenario.source());
        JsonNode sourceManifest = manifest(scenario, raw);

        ProcessorException missing = assertThrows(
                ProcessorException.class,
                () -> new Type04Processor().process(context(
                        scenario,
                        raw,
                        sourceManifest,
                        configuration(null),
                        new FakeArtifactGateway(Map.of()),
                        workingDirectory)));
        assertEquals("TOKENIZATION_KEY_MISSING", missing.code());

        for (String reused : List.of(
                GENERIC_KEY,
                DOCUMENT_KEY,
                PAYMENT_KEY,
                PARTY_KEY,
                ACCOUNT_KEY)) {
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> new Type04Processor().process(context(
                            scenario,
                            raw,
                            sourceManifest,
                            configuration(reused),
                            new FakeArtifactGateway(Map.of()),
                            workingDirectory)));
            assertEquals("TOKENIZATION_KEY_REUSE", exception.code());
        }
    }

    @Test
    void environmentLoadsTedKeyWithoutSerializingAnySecret()
            throws Exception {
        Configuration configuration = Configuration.fromEnvironment(
                Map.ofEntries(
                        Map.entry("SFTP_HOST", "sftp"),
                        Map.entry("SFTP_PORT", "22"),
                        Map.entry("SFTP_PROCESSOR_USER", "processor"),
                        Map.entry(
                                "SFTP_PROCESSOR_PASSWORD",
                                "password"),
                        Map.entry(
                                "SFTP_KNOWN_HOSTS",
                                "/known_hosts"),
                        Map.entry(
                                "NWP_TOKENIZATION_KEY",
                                GENERIC_KEY),
                        Map.entry(
                                "NWP_DOCUMENT_TOKEN_KEY",
                                DOCUMENT_KEY),
                        Map.entry(
                                "NWP_PAYMENT_REFERENCE_KEY",
                                PAYMENT_KEY),
                        Map.entry("NWP_PARTY_TOKEN_KEY", PARTY_KEY),
                        Map.entry(
                                "NWP_ACCOUNT_TOKEN_KEY",
                                ACCOUNT_KEY),
                        Map.entry(
                                "NWP_TED_ACCOUNT_TOKEN_KEY",
                                TED_KEY)));

        assertEquals(TED_KEY, configuration.tedAccountTokenKey());
        String diagnostic = configuration.toString();
        for (String secret : List.of(
                GENERIC_KEY,
                DOCUMENT_KEY,
                PAYMENT_KEY,
                PARTY_KEY,
                ACCOUNT_KEY,
                TED_KEY)) {
            assertFalse(diagnostic.contains(secret));
        }
    }

    @Test
    void exactManifestShapeAndLargeJsonIntegersFailClosed(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] raw = fixtureBytes(scenario.source());
        JsonNode invalid = manifest(scenario, raw);
        ((com.fasterxml.jackson.databind.node.ObjectNode) invalid)
                .put("schema_version", 4_294_967_297L);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type04Processor().process(context(
                        scenario,
                        raw,
                        invalid,
                        configuration(TED_KEY),
                        gateway,
                        workingDirectory)));

        assertEquals("INVALID_MANIFEST", exception.code());
        assertTrue(gateway.published.isEmpty());
    }

    @Test
    void manifestDispatcherPublishesCsvChecksumAndManifestLast(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
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
                List.of(new Type04Processor())).dispatch(
                        scenario.batchId(),
                        "04",
                        configuration(TED_KEY),
                        gateway,
                        workingDirectory);

        assertEquals("succeeded", result.asMap().get("status"));
        assertEquals(scenario.csvSha256(), result.asMap().get("csv_sha256"));
        assertEquals(3, result.asMap().get("row_count"));
        assertEquals(2, result.asMap().get("transfer_count"));
        assertEquals(1, result.asMap().get("return_count"));
        assertEquals("1250.00", result.asMap().get("gross_amount"));
        assertEquals("-250.00", result.asMap().get("return_amount"));
        assertEquals("1000.00", result.asMap().get("net_amount"));
        assertEquals(
                List.of(
                        sourceFilename.replace(".dat", ".csv"),
                        sourceFilename.replace(".dat", ".csv.sha256"),
                        "sanitized-manifest.json"),
                gateway.published.keySet().stream().toList());
        assertEquals(
                "sanitized-manifest.json",
                gateway.readinessManifest);
        assertArrayEquals(
                fixtureBytes(scenario.expectedCsv()),
                gateway.published.get(
                        sourceFilename.replace(".dat", ".csv")));

        JsonNode sanitized = StableJson.parse(
                gateway.published.get("sanitized-manifest.json"));
        assertEquals(
                "04",
                sanitized.path("file_type").path("number").asText());
        assertEquals(
                scenario.csvSha256(),
                sanitized.path("csv_file").path("sha256").asText());
        assertEquals(
                "-250.00",
                sanitized.path("stage_controls").path(
                        "return_amount").asText());
    }

    @Test
    void sourceControlRejectionCreatesNoLocalOrPublishedOutput(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = darkFactoryScenario();
        byte[] raw = fixtureBytes(scenario.source());
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type04Processor().process(context(
                        scenario,
                        raw,
                        manifest(scenario, raw),
                        configuration(TED_KEY),
                        gateway,
                        workingDirectory)));

        assertEquals("SOURCE_CONTROL_NET_MISMATCH", exception.code());
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(workingDirectory.resolve(
                filename(scenario.batchId()).replace(".dat", ".csv"))));
        assertFalse(Files.exists(workingDirectory.resolve(
                "sanitized-manifest.json")));
    }

    @Test
    void wholeOutputCollisionRejectsBeforeAnyPublication(
            @TempDir Path workingDirectory) throws Exception {
        Scenario scenario = acceptedScenarios().getFirst();
        byte[] raw = mutate(
                fixtureBytes(scenario.source()),
                2,
                139,
                162,
                "TRANSFER" + "~".repeat(15));
        JsonNode sourceManifest = manifest(scenario, raw);
        FakeArtifactGateway gateway = new FakeArtifactGateway(Map.of());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new Type04Processor().process(context(
                        scenario,
                        raw,
                        sourceManifest,
                        configuration(TED_KEY),
                        gateway,
                        workingDirectory)));
        String evidence = StableJson.line(
                ProcessorResult.rejected(
                        scenario.batchId(),
                        "04",
                        exception).asMap());

        assertEquals("PRIVACY_BOUNDARY_VIOLATION", exception.code());
        assertFalse(evidence.contains("TRANSFER"));
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(workingDirectory.resolve(
                filename(scenario.batchId()).replace(".dat", ".csv"))));
        assertFalse(Files.exists(workingDirectory.resolve(
                "sanitized-manifest.json")));
    }

    @Test
    void earlyAndCrossRecordRejectionsRedactRestrictedSubstrings()
            throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.dat");
        String account = ascii(records(valid).get(1), 61, 73);
        String identifierContainingAccount =
                "A" + account + "XYZ";
        byte[] unsafeIdentifier = mutate(
                valid,
                2,
                1,
                17,
                identifierContainingAccount);
        ProcessorException unsafe = assertThrows(
                ProcessorException.class,
                () -> Type04Processor.parseRaw(
                        unsafeIdentifier,
                        filename("B202607230000301"),
                        "B202607230000301"));
        String unsafeEvidence = StableJson.line(
                ProcessorResult.rejected(
                        "B202607230000301",
                        "04",
                        unsafe).asMap());
        assertEquals("INVALID_IDENTIFIER", unsafe.code());
        assertFalse(unsafeEvidence.contains(account));
        assertFalse(unsafeEvidence.contains(
                identifierContainingAccount));

        byte[] malformedTransport = removeByte(valid, 56);
        ProcessorException transport = assertThrows(
                ProcessorException.class,
                () -> Type04Processor.parseRaw(
                        malformedTransport,
                        filename("B202607230000301"),
                        "B202607230000301"));
        String transportEvidence = StableJson.line(
                ProcessorResult.rejected(
                        "B202607230000301",
                        "04",
                        transport).asMap());
        assertEquals("INVALID_TRANSPORT", transport.code());
        assertFalse(transportEvidence.contains(account));
    }

    @Test
    void resultEvidenceIsStrictlyAggregateOnly() throws Exception {
        ProcessorResult success = ProcessorResult.type04Succeeded(
                "B202607230000301",
                "sanitized.csv",
                "a".repeat(64),
                3,
                2,
                1,
                "1250.00",
                "-250.00",
                "1000.00");
        assertEquals(
                List.of(
                        "batch_id",
                        "code",
                        "csv_file",
                        "csv_sha256",
                        "gross_amount",
                        "net_amount",
                        "return_amount",
                        "return_count",
                        "row_count",
                        "status",
                        "transfer_count"),
                success.asMap().keySet().stream().toList());
        assertFalse(success.asMap().containsKey("movement_id"));
        assertFalse(success.asMap().containsKey("payer_account_token"));
        assertFalse(success.asMap().containsKey("payer_tax_id_masked"));
    }

    private static void assertContractCode(
            byte[] raw,
            String batchId,
            String expectedCode) throws Exception {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> {
                    Type04Processor.ParsedBatch parsed =
                            Type04Processor.parseRaw(
                                    raw,
                                    filename(batchId),
                                    batchId);
                    Type04Processor.validateSourceControls(
                            parsed,
                            manifestForTrailer(
                                    raw,
                                    batchId));
                },
                expectedCode);
        assertEquals(expectedCode, exception.code());
    }

    private static byte[] poisonTransfer(byte[] record) {
        byte[] poisoned = record.clone();
        System.arraycopy(
                "99999999999999".getBytes(StandardCharsets.US_ASCII),
                0,
                poisoned,
                112,
                14);
        poisoned[126] = 'J';
        poisoned[161] = 'A';
        return poisoned;
    }

    private static JsonNode manifestForTrailer(
            byte[] raw,
            String batchId) throws Exception {
        List<byte[]> physical = records(raw);
        byte[] trailer = physical.getLast();
        String returned = money(trailer, 37, 51);
        if (trailer[36] == '-' && !"0.00".equals(returned)) {
            returned = "-" + returned;
        }
        Map<String, Object> controls = Map.of(
                "currency", "BRL",
                "gross_amount", money(trailer, 22, 36),
                "net_amount", money(trailer, 52, 66),
                "return_amount", returned,
                "return_count", Integer.parseInt(ascii(
                        trailer,
                        15,
                        21)),
                "transfer_count", Integer.parseInt(ascii(
                        trailer,
                        9,
                        15)));
        return StableJson.parse(StableJson.bytes(Map.of(
                "batch_id", batchId,
                "file_type", Map.of(
                        "code", "TED_SETTLE04",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "04"),
                "schema_version", 1,
                "source_controls", controls,
                "source_file", Map.of(
                        "encoding", "US-ASCII",
                        "final_newline", "required",
                        "line_ending", "CRLF",
                        "name", filename(batchId),
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length))));
    }

    private static String money(
            byte[] record,
            int start,
            int end) {
        return new BigDecimal(ascii(record, start, end))
                .movePointLeft(2)
                .setScale(2)
                .toPlainString();
    }

    private static String ascii(
            byte[] value,
            int start,
            int end) {
        return new String(
                value,
                start,
                end - start,
                StandardCharsets.US_ASCII);
    }

    private static byte[] mutate(
            byte[] raw,
            int oneBasedRecord,
            int start,
            int end,
            String replacement) {
        List<byte[]> physical = records(raw);
        byte[] source = physical.get(oneBasedRecord - 1);
        byte[] replacementBytes =
                replacement.getBytes(StandardCharsets.US_ASCII);
        byte[] changed = new byte[
                source.length - (end - start) + replacementBytes.length];
        System.arraycopy(source, 0, changed, 0, start);
        System.arraycopy(
                replacementBytes,
                0,
                changed,
                start,
                replacementBytes.length);
        System.arraycopy(
                source,
                end,
                changed,
                start + replacementBytes.length,
                source.length - end);
        physical.set(oneBasedRecord - 1, changed);
        return join(physical);
    }

    private static byte[] removeByte(byte[] value, int index) {
        byte[] result = new byte[value.length - 1];
        System.arraycopy(value, 0, result, 0, index);
        System.arraycopy(
                value,
                index + 1,
                result,
                index,
                value.length - index - 1);
        return result;
    }

    private static List<byte[]> records(byte[] raw) {
        List<byte[]> result = new ArrayList<>();
        int start = 0;
        for (int index = 0; index + 1 < raw.length; index++) {
            if (raw[index] == '\r' && raw[index + 1] == '\n') {
                result.add(Arrays.copyOfRange(raw, start, index));
                start = index + 2;
                index++;
            }
        }
        return result;
    }

    private static byte[] join(List<byte[]> records) {
        int size = records.stream()
                .mapToInt(record -> record.length + 2)
                .sum();
        byte[] result = new byte[size];
        int offset = 0;
        for (byte[] record : records) {
            System.arraycopy(record, 0, result, offset, record.length);
            offset += record.length;
            result[offset++] = '\r';
            result[offset++] = '\n';
        }
        return result;
    }

    private static ProcessingContext context(
            Scenario scenario,
            byte[] raw,
            JsonNode manifest,
            Configuration configuration,
            ArtifactGateway gateway,
            Path workingDirectory) throws ProcessorException {
        byte[] manifestBytes = StableJson.bytes(manifest);
        return new ProcessingContext(
                scenario.batchId(),
                configuration,
                gateway,
                workingDirectory,
                manifestBytes,
                manifest,
                new ProcessingContext.SourceArtifact(
                        filename(scenario.batchId()),
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
                        "code", "TED_SETTLE04",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "04"),
                "schema_version", 1,
                "source_controls", Map.of(
                        "currency", "BRL",
                        "gross_amount", scenario.grossAmount(),
                        "net_amount", scenario.netAmount(),
                        "return_amount", scenario.returnAmount(),
                        "return_count", scenario.returnCount(),
                        "transfer_count", scenario.transferCount()),
                "source_file", Map.of(
                        "encoding", "US-ASCII",
                        "final_newline", "required",
                        "line_ending", "CRLF",
                        "name", filename(scenario.batchId()),
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length));
    }

    private static Configuration configuration(String tedKey) {
        return new Configuration(
                "unused",
                22,
                "unused",
                "unused",
                Path.of("unused"),
                GENERIC_KEY,
                DOCUMENT_KEY,
                PAYMENT_KEY,
                PARTY_KEY,
                ACCOUNT_KEY,
                tedKey);
    }

    private static List<Scenario> acceptedScenarios() {
        return List.of(
                new Scenario(
                        "valid-minimal.dat",
                        "expected-sanitized.csv",
                        "B202607230000301",
                        2,
                        1,
                        "1250.00",
                        "-250.00",
                        "1000.00",
                        "96ac52ddfc186df6b9e0814767ee2176da0740b9944c7dc1d19e82024e875619"),
                new Scenario(
                        "valid-boundary.dat",
                        "expected-valid-boundary-sanitized.csv",
                        "B200002290000302",
                        1,
                        0,
                        "999999999999.99",
                        "0.00",
                        "999999999999.99",
                        "4a125011ce9bfbd0d0f4c2638774f65609a6dbb0b7be639bb21d4fa75fab507b"),
                new Scenario(
                        "all-returned-zero-net.dat",
                        "expected-all-returned-zero-net-sanitized.csv",
                        "B202607230000304",
                        2,
                        2,
                        "1250.00",
                        "-1250.00",
                        "0.00",
                        "1a92c24dac42e3e01cd410be8aa7e3840981491e21fd143a28ae8bb724c8d9ab"));
    }

    private static Scenario darkFactoryScenario() {
        return new Scenario(
                "df-source-004.dat",
                null,
                "B202607230000305",
                2,
                1,
                "1250.00",
                "-250.00",
                "999.99",
                null);
    }

    private static String filename(String batchId) {
        String date = switch (batchId) {
            case "B200002290000302" -> "20000229";
            default -> "20260723";
        };
        return "NW_TED_SETTLEMENT_"
                + date
                + "_"
                + batchId
                + ".dat";
    }

    private static byte[] fixtureBytes(String filename)
            throws java.io.IOException {
        return Files.readAllBytes(fixtureRoot().resolve(filename));
    }

    private static Path fixtureRoot() {
        return Path.of(System.getProperty(
                "contract.type04.fixture.root",
                "../../contracts/types/04-ted-transfer-settlement/main"))
                .toAbsolutePath()
                .normalize();
    }

    private record Scenario(
            String source,
            String expectedCsv,
            String batchId,
            int transferCount,
            int returnCount,
            String grossAmount,
            String returnAmount,
            String netAmount,
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
                        "Cannot read fake published artifact",
                        exception);
            }
        }

        @Override
        public void close() {
            // No resources are held by the deterministic in-memory gateway.
        }
    }
}
