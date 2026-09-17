package com.northwindpay.legacy.type02;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;
import com.northwindpay.legacy.core.StableJson;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class Type02ProcessorTest {
    private static final String DOCUMENT_KEY =
            "northwind-pay-edp-fixture-document-key-v1";

    @Test
    void canonicalFixturesProduceExactApprovedCsvAndHashes()
            throws Exception {
        assertFixture(
                "valid-minimal.txt",
                "expected-sanitized.csv",
                "B202607230000101",
                "8bd2e4bdb2d7fbea367d5105edae3ff0a56fac091ea9b1072af0821a8e25a20a");
        assertFixture(
                "valid-boundary.txt",
                "expected-valid-boundary-sanitized.csv",
                "B202402290000102",
                "d6169c5ca5838e1a6e1912fea3ba758537d58f7e3e4d8956f175af73be6acf8f");
        assertFixture(
                "escaped-content.txt",
                "expected-escaped-content-sanitized.csv",
                "B202607230000104",
                "89d151896a8dd386377dcd13a5e0607d3d8a52ed01b11d7b9ed8ec13c44f06b5");
    }

    @Test
    void canonicalOutputUsesSeparateExactDocumentTokensAndMasks()
            throws Exception {
        Type02Processor.CsvOutput output = renderFixture(
                "valid-minimal.txt",
                "B202607230000101");
        String csv = new String(
                output.bytes(),
                StandardCharsets.UTF_8);

        assertFalse(csv.contains("12345678909"));
        assertFalse(csv.contains("12345678000195"));
        assertFalse(csv.contains("98765432000198"));
        assertFalse(csv.contains("11144477735"));
        assertFalse(csv.contains("northwind-pay-edp-fixture-key-v1"));
        assertEquals(2, output.rowCount());
        assertEquals(new BigDecimal("200.00"), output.creditAmount());
        assertEquals(new BigDecimal("26.55"), output.debitAmount());
        assertEquals(new BigDecimal("173.45"), output.netAmount());
        assertEquals(1, output.returnedCount());
    }

    @Test
    void malformedFixtureReportsExactFieldCountFailure()
            throws Exception {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> parseFixture(
                        "malformed.txt",
                        "B202607230000103"));

        assertEquals("INVALID_FIELD_COUNT", exception.code());
        assertEquals(2, exception.recordNumber());
        assertNull(exception.transactionId());
    }

    @Test
    void darkFactorySourceReportsIndependentNetControlsOnly()
            throws Exception {
        Type02Processor.ParsedBatch batch = parseFixture(
                "df-source-002.txt",
                "B202607230000105");
        JsonNode manifest = controlsManifest(
                2,
                "200.00",
                "26.55",
                "173.44");

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type02Processor.validateSourceControls(
                        batch,
                        manifest));
        Map<String, Object> result = ProcessorResult.rejected(
                "B202607230000105",
                "02",
                exception).asMap();

        assertEquals(
                "SOURCE_CONTROL_NET_MISMATCH",
                result.get("code"));
        assertEquals(2, result.get("declared_event_count"));
        assertEquals(2, result.get("computed_event_count"));
        assertEquals("200.00", result.get("declared_credit_amount"));
        assertEquals("200.00", result.get("computed_credit_amount"));
        assertEquals("26.55", result.get("declared_debit_amount"));
        assertEquals("26.55", result.get("computed_debit_amount"));
        assertEquals("173.44", result.get("declared_net_amount"));
        assertEquals("173.45", result.get("computed_net_amount"));
    }

    @Test
    void controlValidationUsesDeterministicMismatchPrecedence()
            throws Exception {
        Type02Processor.ParsedBatch canonical = parseFixture(
                "valid-minimal.txt",
                "B202607230000101");
        List<String> codes = List.of(
                "SOURCE_CONTROL_COUNT_MISMATCH",
                "SOURCE_CONTROL_CREDIT_MISMATCH",
                "SOURCE_CONTROL_DEBIT_MISMATCH",
                "SOURCE_CONTROL_NET_MISMATCH");
        List<Type02Processor.ParsedBatch> defects = List.of(
                replaceDeclared(
                        canonical,
                        1,
                        canonical.declaredCredit(),
                        canonical.declaredDebit(),
                        canonical.declaredNet()),
                replaceDeclared(
                        canonical,
                        canonical.declaredCount(),
                        new BigDecimal("199.99"),
                        canonical.declaredDebit(),
                        canonical.declaredNet()),
                replaceDeclared(
                        canonical,
                        canonical.declaredCount(),
                        canonical.declaredCredit(),
                        new BigDecimal("26.54"),
                        canonical.declaredNet()),
                replaceDeclared(
                        canonical,
                        canonical.declaredCount(),
                        canonical.declaredCredit(),
                        canonical.declaredDebit(),
                        new BigDecimal("173.44")));
        for (int index = 0; index < defects.size(); index++) {
            Type02Processor.ParsedBatch defect = defects.get(index);
            JsonNode manifest = controlsManifest(
                    defect.declaredCount(),
                    money(defect.declaredCredit()),
                    money(defect.declaredDebit()),
                    money(defect.declaredNet()));
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type02Processor.validateSourceControls(
                            defect,
                            manifest));
            assertEquals(codes.get(index), exception.code());
        }
    }

    @Test
    void transportIsStrictBeforeRecordParsing() throws Exception {
        byte[] valid = fixtureBytes("valid-minimal.txt");
        byte[] bom = new byte[valid.length + 3];
        System.arraycopy(
                new byte[]{(byte) 0xef, (byte) 0xbb, (byte) 0xbf},
                0,
                bom,
                0,
                3);
        System.arraycopy(valid, 0, bom, 3, valid.length);
        assertParseCode(bom, "B202607230000101", "INVALID_TRANSPORT");

        byte[] invalidUtf8 = Arrays.copyOf(valid, valid.length);
        invalidUtf8[10] = (byte) 0xff;
        assertParseCode(invalidUtf8, "B202607230000101", "INVALID_UTF8");

        assertParseCode(
                Arrays.copyOf(valid, valid.length - 1),
                "B202607230000101",
                "INVALID_TRANSPORT");
        assertParseCode(
                (new String(valid, StandardCharsets.UTF_8) + "\n")
                        .getBytes(StandardCharsets.UTF_8),
                "B202607230000101",
                "INVALID_TRANSPORT");
        assertParseCode(
                new String(valid, StandardCharsets.UTF_8)
                        .replace("\nD|", "\n\nD|")
                        .getBytes(StandardCharsets.UTF_8),
                "B202607230000101",
                "INVALID_TRANSPORT");
        assertParseCode(
                new String(valid, StandardCharsets.UTF_8)
                        .replace("\n", "\r\n")
                        .getBytes(StandardCharsets.UTF_8),
                "B202607230000101",
                "INVALID_TRANSPORT");

        String oversized = "H|" + "A".repeat(511) + "\n"
                + "D|placeholder\nT|1|0.00|0.00|0.00\n";
        assertParseCode(
                oversized.getBytes(StandardCharsets.UTF_8),
                "B202607230000101",
                "INVALID_TRANSPORT");
    }

    @Test
    void lexerRejectsUnknownAndDanglingEscapes() throws Exception {
        String valid = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8);
        assertParseCode(
                valid.replace("Cafe", "Cafe\\q")
                        .getBytes(StandardCharsets.UTF_8),
                "B202402290000102",
                "INVALID_ESCAPE_SEQUENCE");
        assertParseCode(
                valid.replace("Cafe\nT|", "Cafe\\\nT|")
                        .getBytes(StandardCharsets.UTF_8),
                "B202402290000102",
                "INVALID_ESCAPE_SEQUENCE");
    }

    @Test
    void unsignedTrailerCountAllowsContractValidLeadingZeroes()
            throws Exception {
        String valid = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8);
        Type02Processor.ParsedBatch parsed =
                Type02Processor.parseRaw(
                        valid.replace(
                                "T|1|0.01",
                                "T|00001|0.01")
                                .getBytes(StandardCharsets.UTF_8),
                        filename("B202402290000102"),
                        "B202402290000102");

        assertEquals(1, parsed.declaredCount());
    }

    @Test
    void timestampRulesEnforceCanonicalOffsetAndSaoPauloDate()
            throws Exception {
        String valid = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8);
        for (String timestamp : List.of(
                "2024-02-29T23:59:59+00:00",
                "2024-02-29T23:59:59-00:00",
                "2024-02-29T23:59:59.000Z",
                "2024-03-01T03:00:00Z",
                "2024-02-29T23:59:59+19:00")) {
            assertParseCode(
                    valid.replace(
                            "2024-02-29T23:59:59Z",
                            timestamp)
                            .getBytes(StandardCharsets.UTF_8),
                    "B202402290000102",
                    "INVALID_TIMESTAMP");
        }
    }

    @Test
    void descriptionPolicyRejectsNormalizationInjectionAndIdentifiers()
            throws Exception {
        String valid = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8);
        for (String description : List.of(
                "=formula",
                "Cafe\u0301",
                "safe\u202Etext",
                "reference 12345678901",
                "12345678000195",
                "x".repeat(81))) {
            assertParseCode(
                    valid.replace("Cafe", description)
                            .getBytes(StandardCharsets.UTF_8),
                    "B202402290000102",
                    "INVALID_DESCRIPTION");
        }
    }

    @Test
    void emojiZwJDescriptionIsAcceptedAndPreserved()
            throws Exception {
        String description = "Pagamento 👩‍💻";
        String source = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8)
                .replace("Cafe", description);
        Type02Processor.ParsedBatch parsed =
                Type02Processor.parseRaw(
                        source.getBytes(StandardCharsets.UTF_8),
                        filename("B202402290000102"),
                        "B202402290000102");
        Type02Processor.CsvOutput output =
                Type02Processor.renderCsv(
                        parsed,
                        filename("B202402290000102"),
                        DOCUMENT_KEY);

        assertEquals(
                description,
                parsed.events().getFirst().description());
        assertTrue(new String(
                output.bytes(),
                StandardCharsets.UTF_8).contains(description));
    }

    @Test
    void invalidCpfOrCnpjFailsWithoutEchoingRestrictedValues()
            throws Exception {
        String valid = new String(
                fixtureBytes("valid-boundary.txt"),
                StandardCharsets.UTF_8);
        String invalidDocument = "11111111111";
        byte[] source = valid.replace(
                "11144477735",
                invalidDocument).getBytes(StandardCharsets.UTF_8);
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type02Processor.parseRaw(
                        source,
                        filename("B202402290000102"),
                        "B202402290000102"));
        String result = StableJson.line(
                ProcessorResult.rejected(
                        "B202402290000102",
                        "02",
                        exception).asMap());

        assertEquals("INVALID_DOCUMENT", exception.code());
        assertFalse(result.contains(invalidDocument));
        assertFalse(result.contains("Cafe"));
        assertFalse(result.contains("doc_"));
        assertFalse(result.contains("*******"));
    }

    @Test
    void missingSeparateDocumentKeyFailsClosed() throws Exception {
        Type02Processor.ParsedBatch parsed = parseFixture(
                "valid-minimal.txt",
                "B202607230000101");

        for (String key : Arrays.asList(null, "", "   ")) {
            ProcessorException exception = assertThrows(
                    ProcessorException.class,
                    () -> Type02Processor.renderCsv(
                            parsed,
                            filename("B202607230000101"),
                            key));
            assertEquals(
                    "DOCUMENT_TOKEN_KEY_MISSING",
                    exception.code());
        }
    }

    @Test
    void wholeCsvPrivacyScanRejectsAnyRestrictedDocument()
            throws Exception {
        Type02Processor.ParsedBatch parsed = parseFixture(
                "valid-minimal.txt",
                "B202607230000101");
        Type02Processor.Event original =
                parsed.events().getFirst();
        Type02Processor.Event contaminated =
                new Type02Processor.Event(
                        original.recordNumber(),
                        original.endToEndId(),
                        original.transactionId(),
                        original.payerDocumentType(),
                        original.payerDocument(),
                        original.payeeDocumentType(),
                        original.payeeDocument(),
                        original.timestampLexeme(),
                        original.amount(),
                        original.direction(),
                        original.status(),
                        original.returnCode(),
                        original.payerDocument());
        Type02Processor.ParsedBatch contaminatedBatch =
                new Type02Processor.ParsedBatch(
                        parsed.batchId(),
                        parsed.fileDate(),
                        List.of(
                                contaminated,
                                parsed.events().get(1)),
                        parsed.declaredCount(),
                        parsed.declaredCredit(),
                        parsed.declaredDebit(),
                        parsed.declaredNet(),
                        parsed.computedCredit(),
                        parsed.computedDebit(),
                        parsed.computedNet(),
                        parsed.returnedCount());

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type02Processor.renderCsv(
                        contaminatedBatch,
                        filename("B202607230000101"),
                        DOCUMENT_KEY));

        assertEquals(
                "PRIVACY_BOUNDARY_VIOLATION",
                exception.code());
        assertEquals(2, exception.recordNumber());
        assertNull(exception.transactionId());
    }

    private static void assertFixture(
            String source,
            String expected,
            String batchId,
            String expectedHash) throws Exception {
        Type02Processor.CsvOutput output =
                renderFixture(source, batchId);
        assertArrayEquals(
                Files.readAllBytes(fixtureRoot().resolve(expected)),
                output.bytes());
        assertEquals(
                expectedHash,
                ArtifactIO.sha256(output.bytes()));
    }

    private static Type02Processor.CsvOutput renderFixture(
            String source,
            String batchId) throws Exception {
        return Type02Processor.renderCsv(
                parseFixture(source, batchId),
                filename(batchId),
                DOCUMENT_KEY);
    }

    private static Type02Processor.ParsedBatch parseFixture(
            String source,
            String batchId) throws Exception {
        return Type02Processor.parseRaw(
                fixtureBytes(source),
                filename(batchId),
                batchId);
    }

    private static byte[] fixtureBytes(String name)
            throws Exception {
        return Files.readAllBytes(fixtureRoot().resolve(name));
    }

    private static void assertParseCode(
            byte[] source,
            String batchId,
            String code) {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type02Processor.parseRaw(
                        source,
                        filename(batchId),
                        batchId));
        assertEquals(code, exception.code());
    }

    private static JsonNode controlsManifest(
            int count,
            String credit,
            String debit,
            String net) throws Exception {
        String json = """
                {
                  "source_controls": {
                    "credit_amount": "%s",
                    "currency": "BRL",
                    "debit_amount": "%s",
                    "event_count": %d,
                    "net_amount": "%s"
                  }
                }
                """.formatted(credit, debit, count, net);
        return StableJson.parse(
                json.getBytes(StandardCharsets.UTF_8));
    }

    private static Type02Processor.ParsedBatch replaceDeclared(
            Type02Processor.ParsedBatch value,
            int count,
            BigDecimal credit,
            BigDecimal debit,
            BigDecimal net) {
        return new Type02Processor.ParsedBatch(
                value.batchId(),
                value.fileDate(),
                value.events(),
                count,
                credit,
                debit,
                net,
                value.computedCredit(),
                value.computedDebit(),
                value.computedNet(),
                value.returnedCount());
    }

    private static String money(BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static String filename(String batchId) {
        return "NW_INSTANT_PAYMENT_"
                + batchId.substring(1, 9)
                + "_"
                + batchId
                + ".txt";
    }

    private static Path fixtureRoot() {
        String configured = System.getProperty(
                "contract.type02.fixture.root");
        if (configured != null) {
            return Path.of(configured);
        }
        return Path.of(
                "../../contracts/types/02-instant-payment-events/main")
                .toAbsolutePath()
                .normalize();
    }
}
