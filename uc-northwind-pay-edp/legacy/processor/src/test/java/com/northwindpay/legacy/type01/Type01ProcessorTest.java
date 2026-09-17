package com.northwindpay.legacy.type01;

import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;
import com.northwindpay.legacy.core.StableJson;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class Type01ProcessorTest {
    private static final String FIXTURE_KEY = "northwind-pay-edp-fixture-key-v1";

    @Test
    void canonicalFixtureProducesExactApprovedCsv() throws Exception {
        Path root = fixtureRoot();
        byte[] raw = Files.readAllBytes(root.resolve("valid-minimal.dat"));
        Type01Processor.ParsedBatch batch = Type01Processor.parseRaw(
                raw,
                "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                "B202607230000001");
        Type01Processor.CsvOutput output = Type01Processor.renderCsv(
                batch,
                "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                FIXTURE_KEY);

        assertArrayEquals(
                Files.readAllBytes(root.resolve("expected-sanitized.csv")),
                output.bytes());
        assertEquals(2, output.rowCount());
        assertEquals(17_345, output.netAmountMinor());
        assertEquals(
                "a7db2ed1bfe76ab180bba750bbd4d79184d1e118b643a2a0e4d6f0e7f6ec089d",
                Type01Processor.sha256(output.bytes()));
    }

    @Test
    void negativeOverpunchDecodesExactly() throws Exception {
        assertEquals(-1_234, Type01Processor.decodeOverpunch("00000000123M", 2, "TXN0000000000003"));
        assertEquals(5_000, Type01Processor.decodeOverpunch("00000000500{", 2, "TXN0000000000002"));
    }

    @Test
    void boundaryAndRefundFixturesProduceTheirExactApprovedCsv() throws Exception {
        assertFixtureCsv(
                "valid-boundary.dat",
                "expected-valid-boundary-sanitized.csv",
                "NW_CARD_SETTLEMENT_20240229_B202402290000001.dat",
                "B202402290000001");
        assertFixtureCsv(
                "negative-overpunch.dat",
                "expected-negative-overpunch-sanitized.csv",
                "NW_CARD_SETTLEMENT_20260723_B202607230000002.dat",
                "B202607230000002");
    }

    @Test
    void darkFactoryFixturePreservesTheOneCentSourceDefect() throws Exception {
        Path root = fixtureRoot();
        byte[] raw = Files.readAllBytes(root.resolve("df-source-001.dat"));
        Type01Processor.ParsedBatch batch = Type01Processor.parseRaw(
                raw,
                "NW_CARD_SETTLEMENT_20260723_B202607230000004.dat",
                "B202607230000004");
        assertEquals(17_344, batch.declaredNetMinor());
        assertEquals(17_345, batch.computedNetMinor());
    }

    @Test
    void malformedOverpunchReturnsSafePrimaryCode() throws IOException {
        Path root = fixtureRoot();
        byte[] raw = Files.readAllBytes(root.resolve("malformed.dat"));
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.parseRaw(
                        raw,
                        "NW_CARD_SETTLEMENT_20260723_B202607230000003.dat",
                        "B202607230000003"));
        assertEquals("INVALID_OVERPUNCH", exception.code());
        assertEquals(2, exception.recordNumber());
        assertEquals("TXN0000000000004", exception.transactionId());
    }

    @Test
    void sourceControlMismatchReturnsPrivacySafeDeclaredAndComputedControls()
            throws Exception {
        Path root = fixtureRoot();
        Type01Processor.ParsedBatch batch = Type01Processor.parseRaw(
                Files.readAllBytes(root.resolve("df-source-001.dat")),
                "NW_CARD_SETTLEMENT_20260723_B202607230000004.dat",
                "B202607230000004");
        var manifest = StableJson.parse(
                """
                {
                  "source_controls": {
                    "currency": "BRL",
                    "detail_count": 2,
                    "net_amount": "173.44"
                  }
                }
                """.getBytes(StandardCharsets.UTF_8));

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.validateSourceControls(batch, manifest));
        ProcessorResult result = ProcessorResult.type01Rejected(
                "B202607230000004",
                exception);
        Map<String, Object> output = result.asMap();

        assertEquals("SOURCE_CONTROL_TOTAL_MISMATCH", output.get("code"));
        assertEquals(2, output.get("declared_detail_count"));
        assertEquals("173.44", output.get("declared_net_amount"));
        assertEquals(2, output.get("computed_detail_count"));
        assertEquals("173.45", output.get("computed_net_amount"));
        assertEquals(List.of("123.45", "50.00"), output.get("detail_amounts"));
        assertNull(output.get("transaction_id"));
        String serialized = StableJson.line(output);
        for (Type01Processor.Detail detail : batch.details()) {
            assertFalse(serialized.contains(detail.pan()));
            assertFalse(serialized.contains(detail.cpf()));
        }
    }

    @Test
    void trailerCountRequiresExactlySixAsciiDigits()
            throws Exception {
        String source = new String(
                Files.readAllBytes(
                        fixtureRoot().resolve("valid-minimal.dat")),
                StandardCharsets.ISO_8859_1);
        String[] records = source.substring(
                0,
                source.length() - 1).split("\\n", -1);
        String trailer = records[records.length - 1];
        records[records.length - 1] = trailer.substring(0, 9)
                + "+00002"
                + trailer.substring(15);

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.parseRaw(
                        (String.join("\n", records) + "\n").getBytes(
                                StandardCharsets.ISO_8859_1),
                        "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                        "B202607230000001"));

        assertEquals("INVALID_TRAILER", exception.code());
    }

    @Test
    void wholeBatchPrivacyRedactsCrossRecordPanAndCpfSubstrings()
            throws Exception {
        String source = new String(
                Files.readAllBytes(
                        fixtureRoot().resolve("valid-minimal.dat")),
                StandardCharsets.ISO_8859_1);
        String[] canonical = source.substring(
                0,
                source.length() - 1).split("\\n", -1);
        String recordOnePan = canonical[1].substring(33, 49);
        String recordOneCpf = canonical[1].substring(49, 60);

        for (String adversarialTransactionId : List.of(
                recordOnePan,
                "AA" + recordOneCpf + "BBB")) {
            String[] records = canonical.clone();
            String secondDetail = records[2];
            secondDetail = secondDetail.substring(0, 1)
                    + adversarialTransactionId
                    + secondDetail.substring(17);
            records[2] = secondDetail.substring(0, 85)
                    + "!"
                    + secondDetail.substring(86);
            byte[] adversarial = (String.join("\n", records) + "\n")
                    .getBytes(StandardCharsets.ISO_8859_1);

            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type01Processor.parseRaw(
                            adversarial,
                            "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                            "B202607230000001"));
            ProcessorResult result = ProcessorResult.type01Rejected(
                    "B202607230000001",
                    exception);
            String serialized = StableJson.line(result.asMap());

            assertEquals("INVALID_OVERPUNCH", exception.code());
            assertEquals(3, exception.recordNumber());
            assertNull(exception.transactionId());
            assertNull(result.asMap().get("transaction_id"));
            assertFalse(serialized.contains(
                    adversarialTransactionId));
            for (int index = 1;
                    index < records.length - 1;
                    index++) {
                assertFalse(serialized.contains(
                        records[index].substring(33, 49)));
                assertFalse(serialized.contains(
                        records[index].substring(49, 60)));
            }
        }
    }

    @Test
    void transportFailureStillScansEveryDiagnosticResultField()
            throws Exception {
        String source = new String(
                Files.readAllBytes(
                        fixtureRoot().resolve("valid-minimal.dat")),
                StandardCharsets.ISO_8859_1);
        String cpf = source.split("\\n", -1)[1]
                .substring(49, 60);
        String contaminatedBatchId = "B0000" + cpf;

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.parseRaw(
                        source.replace("\n", "\r\n").getBytes(
                                StandardCharsets.ISO_8859_1),
                        "unused.dat",
                        contaminatedBatchId));
        Map<String, Object> result = ProcessorResult.type01Rejected(
                contaminatedBatchId,
                exception).asMap();
        String serialized = StableJson.line(result);

        assertEquals("INVALID_TRANSPORT", exception.code());
        assertNull(result.get("batch_id"));
        assertFalse(serialized.contains(cpf));
    }

    @Test
    void sourceControlsRejectWrongShapesAndTypesWithoutCoercion()
            throws Exception {
        Type01Processor.ParsedBatch batch =
                canonicalParsedBatch();
        List<String> invalidControls = List.of(
                "[]",
                """
                {"currency":1,"detail_count":2,"net_amount":"173.45"}
                """,
                """
                {"currency":"USD","detail_count":2,"net_amount":"173.45"}
                """,
                """
                {"currency":"BRL","detail_count":"2","net_amount":"173.45"}
                """,
                """
                {"currency":"BRL","detail_count":2.0,"net_amount":"173.45"}
                """,
                """
                {"currency":"BRL","detail_count":0,"net_amount":"173.45"}
                """,
                """
                {"currency":"BRL","detail_count":2,"net_amount":173.45}
                """,
                """
                {"currency":"BRL","detail_count":2,"net_amount":"0173.45"}
                """,
                """
                {"currency":"BRL","detail_count":2,"net_amount":"-0.00"}
                """,
                """
                {"currency":"BRL","detail_count":2,"net_amount":"173.45","extra":true}
                """);

        for (String controls : invalidControls) {
            var manifest = StableJson.parse(
                    ("{\"source_controls\":" + controls + "}")
                            .getBytes(StandardCharsets.UTF_8));
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type01Processor.validateSourceControls(
                            batch,
                            manifest));

            assertEquals("INVALID_MANIFEST", exception.code());
        }
    }

    @Test
    void genericRejectionDoesNotExposeDarkFactoryDiagnosticsOrRawIdentifiers()
            throws Exception {
        for (String restrictedIdentifier : List.of(
                "4111111111111111",
                "12345678901")) {
            ProcessorResult result = ProcessorResult.type01Rejected(
                    "B202607230000001",
                    new ProcessorException(
                            "INVALID_DETAIL",
                            "Detail fields violate Type 01",
                            2,
                            restrictedIdentifier));
            Map<String, Object> output = result.asMap();

            assertNull(output.get("declared_detail_count"));
            assertNull(output.get("declared_net_amount"));
            assertNull(output.get("computed_detail_count"));
            assertNull(output.get("computed_net_amount"));
            assertNull(output.get("detail_amounts"));
            assertNull(output.get("transaction_id"));
            assertFalse(
                    StableJson.line(output)
                            .contains(restrictedIdentifier));
        }
    }

    @Test
    void privacyBoundaryRejectsPanCopiedIntoAnotherCsvColumn() throws Exception {
        Type01Processor.ParsedBatch batch = canonicalParsedBatch();
        Type01Processor.Detail original = batch.details().getFirst();
        Type01Processor.Detail contaminated = new Type01Processor.Detail(
                original.recordNumber(),
                original.pan(),
                original.merchantId(),
                original.pan(),
                original.cpf(),
                original.date(),
                original.time(),
                original.amountMinor(),
                original.movement(),
                original.authorizationCode(),
                original.nsu(),
                original.terminalId());
        Type01Processor.ParsedBatch contaminatedBatch = withFirstDetail(
                batch,
                contaminated);

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.renderCsv(
                        contaminatedBatch,
                        "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                        FIXTURE_KEY));

        assertEquals("PRIVACY_BOUNDARY_VIOLATION", exception.code());
        assertEquals(2, exception.recordNumber());
        assertNull(exception.transactionId());
    }

    @Test
    void privacyBoundaryRejectsCpfCopiedIntoAnotherCsvColumn() throws Exception {
        Type01Processor.ParsedBatch batch = canonicalParsedBatch();
        Type01Processor.Detail original = batch.details().getFirst();
        Type01Processor.Detail contaminated = new Type01Processor.Detail(
                original.recordNumber(),
                original.transactionId(),
                "ABCDE" + original.cpf(),
                original.pan(),
                original.cpf(),
                original.date(),
                original.time(),
                original.amountMinor(),
                original.movement(),
                original.authorizationCode(),
                original.nsu(),
                original.terminalId());
        Type01Processor.ParsedBatch contaminatedBatch = withFirstDetail(
                batch,
                contaminated);

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type01Processor.renderCsv(
                        contaminatedBatch,
                        "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                        FIXTURE_KEY));

        assertEquals("PRIVACY_BOUNDARY_VIOLATION", exception.code());
        assertEquals(2, exception.recordNumber());
        assertNull(exception.transactionId());
    }

    private static void assertFixtureCsv(
            String rawFixture,
            String csvFixture,
            String sourceFilename,
            String batchId) throws Exception {
        Path root = fixtureRoot();
        Type01Processor.ParsedBatch batch = Type01Processor.parseRaw(
                Files.readAllBytes(root.resolve(rawFixture)),
                sourceFilename,
                batchId);
        Type01Processor.CsvOutput output = Type01Processor.renderCsv(
                batch,
                sourceFilename,
                FIXTURE_KEY);
        assertArrayEquals(
                Files.readAllBytes(root.resolve(csvFixture)),
                output.bytes());
    }

    private static Type01Processor.ParsedBatch canonicalParsedBatch()
            throws Exception {
        Path root = fixtureRoot();
        return Type01Processor.parseRaw(
                Files.readAllBytes(root.resolve("valid-minimal.dat")),
                "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat",
                "B202607230000001");
    }

    private static Type01Processor.ParsedBatch withFirstDetail(
            Type01Processor.ParsedBatch batch,
            Type01Processor.Detail first) {
        return new Type01Processor.ParsedBatch(
                batch.batchId(),
                batch.fileDate(),
                List.of(first, batch.details().get(1)),
                batch.declaredCount(),
                batch.declaredNetMinor(),
                batch.computedNetMinor());
    }

    private static Path fixtureRoot() {
        String configured = System.getProperty("contract.fixture.root");
        if (configured != null) {
            return Path.of(configured);
        }
        return Path.of("../../contracts/types/01-card-settlement/main").toAbsolutePath().normalize();
    }
}
