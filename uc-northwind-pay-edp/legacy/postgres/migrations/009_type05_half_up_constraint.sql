\set ON_ERROR_STOP on

ALTER TABLE staging.merchant_fee_assessment
    ADD CONSTRAINT merchant_fee_staging_half_up_check CHECK (
        calculated_fee_brl = round(
            gross_amount_brl * rate_percent / 100,
            2
        )
    );

ALTER TABLE legacy.merchant_fee_assessment
    ADD CONSTRAINT merchant_fee_legacy_half_up_check CHECK (
        calculated_fee_brl = round(
            gross_amount_brl * rate_percent / 100,
            2
        )
    );

COMMENT ON CONSTRAINT merchant_fee_staging_half_up_check
    ON staging.merchant_fee_assessment IS
'Independently enforces positive-value HALF_UP fee arithmetic at COPY time.';

COMMENT ON CONSTRAINT merchant_fee_legacy_half_up_check
    ON legacy.merchant_fee_assessment IS
'Preserves the exact Type 05 fee calculation in the operational boundary.';
