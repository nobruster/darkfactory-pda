package com.northwindpay.legacy.core;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Privacy-safe checked failure raised at a legacy processing boundary.
 *
 * <p>Only aggregate controls and explicitly safe record context may be
 * attached. Raw source text, documents, descriptions, tokens, and masks are
 * never exception fields.
 */
public final class ProcessorException extends Exception {
    private final String code;
    private final Integer recordNumber;
    private final String transactionId;
    private final Type01Controls type01Controls;
    private final Type02Controls type02Controls;
    private final Type03Controls type03Controls;
    private final Type04Controls type04Controls;
    private final Type05Controls type05Controls;
    private DiagnosticPrivacy diagnosticPrivacy =
            DiagnosticPrivacy.fromRestrictedValues(List.of());
    private String typeNumber;

    /**
     * Creates a failure without record or aggregate diagnostics.
     */
    public ProcessorException(String code, String message) {
        this(
                code,
                message,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null);
    }

    /**
     * Creates a failure whose cause is retained for control flow, never
     * serialized to the process result.
     */
    public ProcessorException(
            String code,
            String message,
            Throwable cause) {
        this(
                code,
                message,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                cause);
    }

    /**
     * Creates a record-scoped failure. Callers must pass only a validated,
     * privacy-safe transaction ID; Type 02 deliberately always passes null.
     */
    public ProcessorException(
            String code,
            String message,
            Integer recordNumber,
            String transactionId) {
        this(
                code,
                message,
                recordNumber,
                transactionId,
                null,
                null,
                null,
                null,
                null,
                null);
    }

    private ProcessorException(
            String code,
            String message,
            Integer recordNumber,
            String transactionId,
            Type01Controls type01Controls,
            Type02Controls type02Controls,
            Type03Controls type03Controls,
            Type04Controls type04Controls,
            Type05Controls type05Controls,
            Throwable cause) {
        super(message, cause);
        this.code = code;
        this.recordNumber = recordNumber;
        this.transactionId = transactionId;
        this.type01Controls = type01Controls;
        this.type02Controls = type02Controls;
        this.type03Controls = type03Controls;
        this.type04Controls = type04Controls;
        this.type05Controls = type05Controls;
    }

    /**
     * Creates the original Type 01 aggregate control finding.
     */
    public static ProcessorException type01SourceControlMismatch(
            int declaredDetailCount,
            String declaredNetAmount,
            int computedDetailCount,
            String computedNetAmount,
            List<String> detailAmounts) {
        return new ProcessorException(
                "SOURCE_CONTROL_TOTAL_MISMATCH",
                "Declared source controls do not match independently parsed details",
                null,
                null,
                new Type01Controls(
                        declaredDetailCount,
                        declaredNetAmount,
                        computedDetailCount,
                        computedNetAmount,
                        List.copyOf(detailAmounts)),
                null,
                null,
                null,
                null,
                null);
    }

    /**
     * Creates a Type 02 aggregate control finding.
     */
    public static ProcessorException type02SourceControlMismatch(
            String code,
            int declaredEventCount,
            String declaredCreditAmount,
            String declaredDebitAmount,
            String declaredNetAmount,
            int computedEventCount,
            String computedCreditAmount,
            String computedDebitAmount,
            String computedNetAmount) {
        return new ProcessorException(
                code,
                "Declared source controls do not match independently parsed events",
                null,
                null,
                null,
                new Type02Controls(
                        declaredEventCount,
                        declaredCreditAmount,
                        declaredDebitAmount,
                        declaredNetAmount,
                        computedEventCount,
                        computedCreditAmount,
                        computedDebitAmount,
                        computedNetAmount),
                null,
                null,
                null,
                null);
    }

    /**
     * Creates a Type 03 aggregate source-control finding.
     *
     * <p>The values are restricted to counts and canonical monetary
     * aggregates. No settlement, document, account, name, mask, or token may
     * be supplied.
     */
    public static ProcessorException type03SourceControlMismatch(
            String code,
            int declaredLotCount,
            int declaredPhysicalRecordCount,
            int declaredLogicalCount,
            String declaredFaceAmount,
            String declaredDiscountAmount,
            String declaredFeeAmount,
            String declaredNetAmount,
            int computedLotCount,
            int computedPhysicalRecordCount,
            int computedLogicalCount,
            String computedFaceAmount,
            String computedDiscountAmount,
            String computedFeeAmount,
            String computedNetAmount,
            int computedOrphanSegmentCount) {
        return new ProcessorException(
                code,
                "Declared Type 03 controls do not match parsed settlements",
                null,
                null,
                null,
                null,
                new Type03Controls(
                        declaredLotCount,
                        declaredPhysicalRecordCount,
                        declaredLogicalCount,
                        declaredFaceAmount,
                        declaredDiscountAmount,
                        declaredFeeAmount,
                        declaredNetAmount,
                        computedLotCount,
                        computedPhysicalRecordCount,
                        computedLogicalCount,
                        computedFaceAmount,
                        computedDiscountAmount,
                        computedFeeAmount,
                        computedNetAmount,
                        computedOrphanSegmentCount),
                null,
                null,
                null);
    }

    /**
     * Creates a Type 04 aggregate source-control finding.
     *
     * <p>Only counts and canonical signed monetary aggregates are retained.
     * Movement identifiers, account tokens, masks, and source values are
     * deliberately excluded.
     *
     * @param code stable source-control rejection code
     * @param declaredTransferCount trailer transfer count
     * @param declaredReturnCount trailer return count
     * @param declaredGrossAmount canonical trailer gross
     * @param declaredReturnAmount canonical signed trailer return
     * @param declaredNetAmount canonical trailer net
     * @param computedTransferCount parsed transfer count
     * @param computedReturnCount parsed return count
     * @param computedGrossAmount independently summed gross
     * @param computedReturnAmount independently summed signed return
     * @param computedNetAmount independently computed net
     * @return aggregate-only Type 04 failure
     */
    public static ProcessorException type04SourceControlMismatch(
            String code,
            int declaredTransferCount,
            int declaredReturnCount,
            String declaredGrossAmount,
            String declaredReturnAmount,
            String declaredNetAmount,
            int computedTransferCount,
            int computedReturnCount,
            String computedGrossAmount,
            String computedReturnAmount,
            String computedNetAmount) {
        return new ProcessorException(
                code,
                "Declared Type 04 controls do not match parsed movements",
                null,
                null,
                null,
                null,
                null,
                new Type04Controls(
                        declaredTransferCount,
                        declaredReturnCount,
                        declaredGrossAmount,
                        declaredReturnAmount,
                        declaredNetAmount,
                        computedTransferCount,
                        computedReturnCount,
                        computedGrossAmount,
                        computedReturnAmount,
                        computedNetAmount),
                null,
                null);
    }

    /**
     * Creates a Type 05 aggregate source-control finding.
     *
     * <p>Only the four declared and independently computed controls are
     * retained. Merchant identifiers, descriptions, CNPJs, masks, and source
     * records are deliberately excluded from the exception.
     *
     * @param code stable source-control rejection code
     * @param declaredRowCount source-manifest row count
     * @param declaredGrossAmount source-manifest gross sum
     * @param declaredAssessedFee source-manifest assessed-fee sum
     * @param declaredCalculatedFee source-manifest calculated-fee sum
     * @param computedRowCount independently parsed row count
     * @param computedGrossAmount independently summed gross
     * @param computedAssessedFee independently summed assessed fee
     * @param computedCalculatedFee independently calculated fee sum
     * @return aggregate-only Type 05 failure
     */
    public static ProcessorException type05SourceControlMismatch(
            String code,
            int declaredRowCount,
            String declaredGrossAmount,
            String declaredAssessedFee,
            String declaredCalculatedFee,
            int computedRowCount,
            String computedGrossAmount,
            String computedAssessedFee,
            String computedCalculatedFee) {
        return new ProcessorException(
                code,
                "Declared Type 05 controls do not match parsed assessments",
                null,
                null,
                null,
                null,
                null,
                null,
                new Type05Controls(
                        declaredRowCount,
                        declaredGrossAmount,
                        declaredAssessedFee,
                        declaredCalculatedFee,
                        computedRowCount,
                        computedGrossAmount,
                        computedAssessedFee,
                        computedCalculatedFee),
                null);
    }

    /**
     * Returns the stable rejection code.
     */
    public String code() {
        return code;
    }

    /**
     * Associates this failure with the manifest-selected processor without
     * changing its privacy-safe diagnostic fields.
     */
    public ProcessorException forType(String selectedTypeNumber) {
        if (typeNumber == null) {
            typeNumber = selectedTypeNumber;
        }
        return this;
    }

    /**
     * Returns the manifest-selected processor type when dispatch reached one.
     */
    public String typeNumber() {
        return typeNumber;
    }

    /**
     * Attaches a clear-value-free matcher used by every diagnostic accessor
     * and by final result serialization.
     */
    public ProcessorException withDiagnosticPrivacy(
            DiagnosticPrivacy privacy) {
        diagnosticPrivacy = Objects.requireNonNull(
                privacy,
                "privacy");
        return this;
    }

    Map<String, Object> redactDiagnosticResult(
            Map<String, Object> result) {
        return diagnosticPrivacy.redactResult(result);
    }

    /**
     * Returns the one-based physical source record, when safe and relevant.
     */
    public Integer recordNumber() {
        return recordNumber;
    }

    /**
     * Returns a validated Type 01 transaction ID, never a Type 02 identifier.
     */
    public String transactionId() {
        return diagnosticPrivacy.redact(transactionId);
    }

    public Integer declaredDetailCount() {
        return type01Controls == null
                ? null
                : type01Controls.declaredCount();
    }

    public String declaredNetAmount() {
        if (type04Controls != null) {
            return diagnosticPrivacy.redact(
                    type04Controls.declaredNet());
        }
        if (type03Controls != null) {
            return diagnosticPrivacy.redact(
                    type03Controls.declaredNet());
        }
        if (type02Controls != null) {
            return diagnosticPrivacy.redact(
                    type02Controls.declaredNet());
        }
        return type01Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type01Controls.declaredNet());
    }

    public Integer computedDetailCount() {
        return type01Controls == null
                ? null
                : type01Controls.computedCount();
    }

    public String computedNetAmount() {
        if (type04Controls != null) {
            return diagnosticPrivacy.redact(
                    type04Controls.computedNet());
        }
        if (type03Controls != null) {
            return diagnosticPrivacy.redact(
                    type03Controls.computedNet());
        }
        if (type02Controls != null) {
            return diagnosticPrivacy.redact(
                    type02Controls.computedNet());
        }
        return type01Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type01Controls.computedNet());
    }

    public List<String> detailAmounts() {
        if (type01Controls == null
                || diagnosticPrivacy.containsRestrictedValue(
                        type01Controls.detailAmounts())) {
            return null;
        }
        return type01Controls.detailAmounts();
    }

    public Integer declaredEventCount() {
        return type02Controls == null
                ? null
                : type02Controls.declaredCount();
    }

    public String declaredCreditAmount() {
        return type02Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type02Controls.declaredCredit());
    }

    public String declaredDebitAmount() {
        return type02Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type02Controls.declaredDebit());
    }

    public Integer computedEventCount() {
        return type02Controls == null
                ? null
                : type02Controls.computedCount();
    }

    public String computedCreditAmount() {
        return type02Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type02Controls.computedCredit());
    }

    public String computedDebitAmount() {
        return type02Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type02Controls.computedDebit());
    }

    public Integer declaredLotCount() {
        return type03Controls == null
                ? null
                : type03Controls.declaredLotCount();
    }

    public Integer declaredPhysicalRecordCount() {
        return type03Controls == null
                ? null
                : type03Controls.declaredPhysicalRecordCount();
    }

    public Integer declaredLogicalCount() {
        return type03Controls == null
                ? null
                : type03Controls.declaredLogicalCount();
    }

    public String declaredFaceAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.declaredFace());
    }

    public String declaredDiscountAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.declaredDiscount());
    }

    public String declaredFeeAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.declaredFee());
    }

    public Integer computedLotCount() {
        return type03Controls == null
                ? null
                : type03Controls.computedLotCount();
    }

    public Integer computedPhysicalRecordCount() {
        return type03Controls == null
                ? null
                : type03Controls.computedPhysicalRecordCount();
    }

    public Integer computedLogicalCount() {
        return type03Controls == null
                ? null
                : type03Controls.computedLogicalCount();
    }

    public String computedFaceAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.computedFace());
    }

    public String computedDiscountAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.computedDiscount());
    }

    public String computedFeeAmount() {
        return type03Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type03Controls.computedFee());
    }

    public Integer computedOrphanSegmentCount() {
        return type03Controls == null
                ? null
                : type03Controls.computedOrphanSegmentCount();
    }

    /**
     * Returns the Type 04 trailer transfer count, when attached.
     *
     * @return declared transfer count or {@code null}
     */
    public Integer declaredTransferCount() {
        return type04Controls == null
                ? null
                : type04Controls.declaredTransferCount();
    }

    /**
     * Returns the Type 04 trailer return count, when attached.
     *
     * @return declared return count or {@code null}
     */
    public Integer declaredReturnCount() {
        return type04Controls == null
                ? null
                : type04Controls.declaredReturnCount();
    }

    /**
     * Returns the Type 04 trailer or Type 05 manifest gross amount.
     *
     * @return declared gross amount or {@code null}
     */
    public String declaredGrossAmount() {
        if (type05Controls != null) {
            return diagnosticPrivacy.redact(
                    type05Controls.declaredGross());
        }
        return type04Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type04Controls.declaredGross());
    }

    /**
     * Returns the Type 04 signed trailer return amount, when attached.
     *
     * @return declared signed return amount or {@code null}
     */
    public String declaredReturnAmount() {
        return type04Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type04Controls.declaredReturn());
    }

    /**
     * Returns the independently parsed Type 04 transfer count.
     *
     * @return computed transfer count or {@code null}
     */
    public Integer computedTransferCount() {
        return type04Controls == null
                ? null
                : type04Controls.computedTransferCount();
    }

    /**
     * Returns the independently parsed Type 04 return count.
     *
     * @return computed return count or {@code null}
     */
    public Integer computedReturnCount() {
        return type04Controls == null
                ? null
                : type04Controls.computedReturnCount();
    }

    /**
     * Returns the independently computed Type 04 or Type 05 gross amount.
     *
     * @return computed gross amount or {@code null}
     */
    public String computedGrossAmount() {
        if (type05Controls != null) {
            return diagnosticPrivacy.redact(
                    type05Controls.computedGross());
        }
        return type04Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type04Controls.computedGross());
    }

    /**
     * Returns the independently computed signed Type 04 return amount.
     *
     * @return computed signed return amount or {@code null}
     */
    public String computedReturnAmount() {
        return type04Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type04Controls.computedReturn());
    }

    /**
     * Returns the Type 05 source-manifest row count, when attached.
     *
     * @return declared row count or {@code null}
     */
    public Integer declaredRowCount() {
        return type05Controls == null
                ? null
                : type05Controls.declaredRowCount();
    }

    /**
     * Returns the independently parsed Type 05 row count, when attached.
     *
     * @return computed row count or {@code null}
     */
    public Integer computedRowCount() {
        return type05Controls == null
                ? null
                : type05Controls.computedRowCount();
    }

    /**
     * Returns the Type 05 source-manifest assessed-fee sum.
     *
     * @return declared assessed-fee sum or {@code null}
     */
    public String declaredAssessedFee() {
        return type05Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type05Controls.declaredAssessedFee());
    }

    /**
     * Returns the independently summed Type 05 assessed fees.
     *
     * @return computed assessed-fee sum or {@code null}
     */
    public String computedAssessedFee() {
        return type05Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type05Controls.computedAssessedFee());
    }

    /**
     * Returns the Type 05 source-manifest calculated-fee sum.
     *
     * @return declared calculated-fee sum or {@code null}
     */
    public String declaredCalculatedFee() {
        return type05Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type05Controls.declaredCalculatedFee());
    }

    /**
     * Returns the independently calculated Type 05 fee sum.
     *
     * @return computed calculated-fee sum or {@code null}
     */
    public String computedCalculatedFee() {
        return type05Controls == null
                ? null
                : diagnosticPrivacy.redact(
                        type05Controls.computedCalculatedFee());
    }

    private record Type01Controls(
            int declaredCount,
            String declaredNet,
            int computedCount,
            String computedNet,
            List<String> detailAmounts) {
    }

    private record Type02Controls(
            int declaredCount,
            String declaredCredit,
            String declaredDebit,
            String declaredNet,
            int computedCount,
            String computedCredit,
            String computedDebit,
            String computedNet) {
    }

    private record Type03Controls(
            int declaredLotCount,
            int declaredPhysicalRecordCount,
            int declaredLogicalCount,
            String declaredFace,
            String declaredDiscount,
            String declaredFee,
            String declaredNet,
            int computedLotCount,
            int computedPhysicalRecordCount,
            int computedLogicalCount,
            String computedFace,
            String computedDiscount,
            String computedFee,
            String computedNet,
            int computedOrphanSegmentCount) {
    }

    private record Type04Controls(
            int declaredTransferCount,
            int declaredReturnCount,
            String declaredGross,
            String declaredReturn,
            String declaredNet,
            int computedTransferCount,
            int computedReturnCount,
            String computedGross,
            String computedReturn,
            String computedNet) {
    }

    private record Type05Controls(
            int declaredRowCount,
            String declaredGross,
            String declaredAssessedFee,
            String declaredCalculatedFee,
            int computedRowCount,
            String computedGross,
            String computedAssessedFee,
            String computedCalculatedFee) {
    }
}
