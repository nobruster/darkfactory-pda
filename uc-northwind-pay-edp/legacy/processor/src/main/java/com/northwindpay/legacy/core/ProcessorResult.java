package com.northwindpay.legacy.core;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Privacy-safe structured outcome emitted by the processor command.
 *
 * <p>Type 01 retains its original field set exactly. Later types expose only
 * aggregate controls and a physical record number; descriptions, documents,
 * tokens, masks, and source records are intentionally impossible to attach.
 */
public final class ProcessorResult {
    private final Map<String, Object> value;

    private ProcessorResult(Map<String, Object> value) {
        this.value = Collections.unmodifiableMap(
                new LinkedHashMap<>(value));
    }

    /**
     * Builds the original Type 01 success result.
     */
    public static ProcessorResult type01Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            String netAmount) {
        LinkedHashMap<String, Object> result = type01Base(batchId);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("net_amount", netAmount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        return new ProcessorResult(result);
    }

    /**
     * Builds a Type 02 success result from independently computed controls.
     */
    public static ProcessorResult type02Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            String creditAmount,
            String debitAmount,
            String netAmount,
            int returnedCount) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", null);
        result.put("credit_amount", creditAmount);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("debit_amount", debitAmount);
        result.put("net_amount", netAmount);
        result.put("returned_count", returnedCount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        return new ProcessorResult(result);
    }

    /**
     * Builds a Type 03 success result from independently computed controls.
     */
    public static ProcessorResult type03Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            String faceAmount,
            String discountAmount,
            String feeAmount,
            String netAmount,
            int orphanSegmentCount) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", null);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("discount_amount", discountAmount);
        result.put("face_amount", faceAmount);
        result.put("fee_amount", feeAmount);
        result.put("net_amount", netAmount);
        result.put("orphan_segment_count", orphanSegmentCount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        return new ProcessorResult(result);
    }

    /**
     * Builds a Type 04 success result from independently computed signed
     * movement controls.
     *
     * @param batchId controlled batch identifier
     * @param csvFile controlled sanitized filename
     * @param csvSha256 lowercase CSV SHA-256
     * @param rowCount total movement rows
     * @param transferCount transfer rows
     * @param returnCount return rows
     * @param grossAmount canonical positive transfer sum
     * @param returnAmount canonical signed return sum
     * @param netAmount canonical net sum
     * @return immutable aggregate-only result
     */
    public static ProcessorResult type04Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            int transferCount,
            int returnCount,
            String grossAmount,
            String returnAmount,
            String netAmount) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", null);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("gross_amount", grossAmount);
        result.put("net_amount", netAmount);
        result.put("return_amount", returnAmount);
        result.put("return_count", returnCount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        result.put("transfer_count", transferCount);
        return new ProcessorResult(result);
    }

    /**
     * Builds a Type 05 success result from independently computed fee
     * controls.
     *
     * @param batchId controlled batch identifier
     * @param csvFile controlled sanitized filename
     * @param csvSha256 lowercase CSV SHA-256
     * @param rowCount total assessment rows
     * @param grossAmount canonical gross sum
     * @param assessedFee canonical assessed-fee sum
     * @param calculatedFee canonical independently calculated-fee sum
     * @return immutable aggregate-only result
     */
    public static ProcessorResult type05Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            String grossAmount,
            String assessedFee,
            String calculatedFee) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("assessed_fee", assessedFee);
        result.put("batch_id", batchId);
        result.put("calculated_fee", calculatedFee);
        result.put("code", null);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("gross_amount", grossAmount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        return new ProcessorResult(result);
    }

    /**
     * Builds a Type 06 success result from independently computed
     * chargeback controls.
     *
     * @param batchId controlled batch identifier
     * @param csvFile controlled sanitized filename
     * @param csvSha256 lowercase CSV SHA-256
     * @param rowCount total chargeback rows
     * @param originalAmount canonical original-amount sum
     * @param chargebackAmount canonical chargeback-amount sum
     * @param calculatedAmount canonical independently calculated sum
     * @return immutable aggregate-only result
     */
    public static ProcessorResult type06Succeeded(
            String batchId,
            String csvFile,
            String csvSha256,
            int rowCount,
            String originalAmount,
            String chargebackAmount,
            String calculatedAmount) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("calculated_amount", calculatedAmount);
        result.put("chargeback_amount", chargebackAmount);
        result.put("code", null);
        result.put("csv_file", csvFile);
        result.put("csv_sha256", csvSha256);
        result.put("original_amount", originalAmount);
        result.put("row_count", rowCount);
        result.put("status", "succeeded");
        return new ProcessorResult(result);
    }

    /**
     * Builds the original Type 01 rejection result.
     */
    public static ProcessorResult type01Rejected(
            String batchId,
            ProcessorException exception) {
        LinkedHashMap<String, Object> result = type01Base(batchId);
        result.put("code", exception.code());
        result.put("computed_detail_count", exception.computedDetailCount());
        result.put("computed_net_amount", exception.computedNetAmount());
        result.put("declared_detail_count", exception.declaredDetailCount());
        result.put("declared_net_amount", exception.declaredNetAmount());
        result.put("detail_amounts", exception.detailAmounts());
        result.put("record_number", exception.recordNumber());
        result.put(
                "transaction_id",
                privacySafeTransactionId(exception.transactionId()));
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    /**
     * Builds a rejection matching the selected processor's evidence policy.
     */
    public static ProcessorResult rejected(
            String batchId,
            String typeNumber,
            ProcessorException exception) {
        if ("06".equals(typeNumber)) {
            return type06Rejected(batchId, exception);
        }
        if ("05".equals(typeNumber)) {
            return type05Rejected(batchId, exception);
        }
        if ("04".equals(typeNumber)) {
            return type04Rejected(batchId, exception);
        }
        if ("03".equals(typeNumber)) {
            return type03Rejected(batchId, exception);
        }
        if (!"02".equals(typeNumber)) {
            return type01Rejected(batchId, exception);
        }
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", exception.code());
        result.put(
                "computed_credit_amount",
                exception.computedCreditAmount());
        result.put(
                "computed_debit_amount",
                exception.computedDebitAmount());
        result.put("computed_event_count", exception.computedEventCount());
        result.put("computed_net_amount", exception.computedNetAmount());
        result.put(
                "declared_credit_amount",
                exception.declaredCreditAmount());
        result.put(
                "declared_debit_amount",
                exception.declaredDebitAmount());
        result.put("declared_event_count", exception.declaredEventCount());
        result.put("declared_net_amount", exception.declaredNetAmount());
        result.put("record_number", exception.recordNumber());
        result.put("status", "rejected");
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    private static ProcessorResult type03Rejected(
            String batchId,
            ProcessorException exception) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", exception.code());
        result.put(
                "computed_discount_amount",
                exception.computedDiscountAmount());
        result.put(
                "computed_face_amount",
                exception.computedFaceAmount());
        result.put(
                "computed_fee_amount",
                exception.computedFeeAmount());
        result.put(
                "computed_logical_count",
                exception.computedLogicalCount());
        result.put(
                "computed_lot_count",
                exception.computedLotCount());
        result.put(
                "computed_net_amount",
                exception.computedNetAmount());
        result.put(
                "computed_orphan_segment_count",
                exception.computedOrphanSegmentCount());
        result.put(
                "computed_physical_record_count",
                exception.computedPhysicalRecordCount());
        result.put(
                "declared_discount_amount",
                exception.declaredDiscountAmount());
        result.put(
                "declared_face_amount",
                exception.declaredFaceAmount());
        result.put(
                "declared_fee_amount",
                exception.declaredFeeAmount());
        result.put(
                "declared_logical_count",
                exception.declaredLogicalCount());
        result.put(
                "declared_lot_count",
                exception.declaredLotCount());
        result.put(
                "declared_net_amount",
                exception.declaredNetAmount());
        result.put(
                "declared_physical_record_count",
                exception.declaredPhysicalRecordCount());
        result.put("record_number", exception.recordNumber());
        result.put("status", "rejected");
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    private static ProcessorResult type04Rejected(
            String batchId,
            ProcessorException exception) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", exception.code());
        result.put(
                "computed_gross_amount",
                exception.computedGrossAmount());
        result.put(
                "computed_net_amount",
                exception.computedNetAmount());
        result.put(
                "computed_return_amount",
                exception.computedReturnAmount());
        result.put(
                "computed_return_count",
                exception.computedReturnCount());
        result.put(
                "computed_transfer_count",
                exception.computedTransferCount());
        result.put(
                "declared_gross_amount",
                exception.declaredGrossAmount());
        result.put(
                "declared_net_amount",
                exception.declaredNetAmount());
        result.put(
                "declared_return_amount",
                exception.declaredReturnAmount());
        result.put(
                "declared_return_count",
                exception.declaredReturnCount());
        result.put(
                "declared_transfer_count",
                exception.declaredTransferCount());
        result.put("record_number", exception.recordNumber());
        result.put("status", "rejected");
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    private static ProcessorResult type05Rejected(
            String batchId,
            ProcessorException exception) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", exception.code());
        result.put(
                "computed_assessed_fee",
                exception.computedAssessedFee());
        result.put(
                "computed_calculated_fee",
                exception.computedCalculatedFee());
        result.put(
                "computed_gross_amount",
                exception.computedGrossAmount());
        result.put(
                "computed_row_count",
                exception.computedRowCount());
        result.put(
                "declared_assessed_fee",
                exception.declaredAssessedFee());
        result.put(
                "declared_calculated_fee",
                exception.declaredCalculatedFee());
        result.put(
                "declared_gross_amount",
                exception.declaredGrossAmount());
        result.put(
                "declared_row_count",
                exception.declaredRowCount());
        result.put("record_number", exception.recordNumber());
        result.put("status", "rejected");
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    private static ProcessorResult type06Rejected(
            String batchId,
            ProcessorException exception) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", exception.code());
        result.put(
                "computed_calculated_amount",
                exception.computedCalculatedFee());
        result.put(
                "computed_chargeback_amount",
                exception.computedAssessedFee());
        result.put(
                "computed_original_amount",
                exception.computedGrossAmount());
        result.put(
                "computed_row_count",
                exception.computedRowCount());
        result.put(
                "declared_calculated_amount",
                exception.declaredCalculatedFee());
        result.put(
                "declared_chargeback_amount",
                exception.declaredAssessedFee());
        result.put(
                "declared_original_amount",
                exception.declaredGrossAmount());
        result.put(
                "declared_row_count",
                exception.declaredRowCount());
        result.put("record_number", exception.recordNumber());
        result.put("status", "rejected");
        return new ProcessorResult(
                exception.redactDiagnosticResult(result));
    }

    /**
     * Returns a stable, immutable result view suitable for JSON encoding.
     */
    public Map<String, Object> asMap() {
        return value;
    }

    private static LinkedHashMap<String, Object> type01Base(String batchId) {
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        result.put("batch_id", batchId);
        result.put("code", null);
        result.put("csv_file", null);
        result.put("csv_sha256", null);
        result.put("computed_detail_count", null);
        result.put("computed_net_amount", null);
        result.put("declared_detail_count", null);
        result.put("declared_net_amount", null);
        result.put("detail_amounts", null);
        result.put("net_amount", null);
        result.put("record_number", null);
        result.put("row_count", null);
        result.put("status", "rejected");
        result.put("transaction_id", null);
        return result;
    }

    private static String privacySafeTransactionId(String transactionId) {
        if (transactionId != null
                && transactionId.matches("(?:[0-9]{11}|[0-9]{16})")) {
            return null;
        }
        return transactionId;
    }
}
