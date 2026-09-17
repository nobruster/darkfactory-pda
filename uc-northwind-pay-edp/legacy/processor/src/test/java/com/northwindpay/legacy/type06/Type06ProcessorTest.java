package com.northwindpay.legacy.type06;

import com.northwindpay.legacy.core.ProcessorException;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Proves Type 06 accepts HALF_UP source 1.01 and plants HALF_EVEN 1.00.
 */
class Type06ProcessorTest {
    private static final String BATCH_ID = "B202607230000501";
    private static final String FILENAME =
            "NW_MERCHANT_CHARGEBACK_20260723_" + BATCH_ID + ".csv";
    private static final String HEADER = String.join(";",
            "chargeback_id",
            "batch_id",
            "merchant_id",
            "merchant_tax_id",
            "reason_code",
            "description",
            "original_amount_brl",
            "rate_percent",
            "chargeback_amount_brl",
            "business_date");
    private static final String VALID_ROW = String.join(";",
            "CBK2026072305001",
            BATCH_ID,
            "MER0000000000001",
            "12345678000195",
            "FRAUD",
            "\"Ajuste de chargeback\"",
            "67,00",
            "1,500",
            "1,01",
            "23/07/2026");

    @Test
    void sourceHalfUpOneCentRendersHalfEven() throws Exception {
        byte[] raw = (HEADER + "\n" + VALID_ROW + "\n")
                .getBytes(StandardCharsets.UTF_8);
        Type06Processor.ParsedBatch parsed = Type06Processor.parseRaw(
                raw,
                FILENAME,
                BATCH_ID);
        assertEquals("1.01", parsed.computedAssessedFee().toPlainString());
        assertEquals("1.01", parsed.computedCalculatedFee().toPlainString());

        Type06Processor.CsvOutput output = Type06Processor.renderCsv(
                parsed,
                FILENAME);
        String csv = new String(output.bytes(), StandardCharsets.UTF_8);
        assertTrue(csv.contains("1.00"));
        assertTrue(csv.contains("HALF_EVEN"));
        assertEquals("1.00", output.assessedFee().toPlainString());
        assertEquals("1.00", output.calculatedFee().toPlainString());
    }

    @Test
    void unquotedDescriptionIsInvalidCsvQuoting() {
        String bad = VALID_ROW.replace("\"Ajuste de chargeback\"", "bad;unquoted");
        byte[] raw = (HEADER + "\n" + bad + "\n")
                .getBytes(StandardCharsets.UTF_8);
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> Type06Processor.parseRaw(raw, FILENAME, BATCH_ID));
        assertEquals("INVALID_CSV_QUOTING", exception.code());
    }
}
