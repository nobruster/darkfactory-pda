-- legacy.apply_merchant_fee_batch  dump 2026-06-22
CREATE PROCEDURE legacy.apply_merchant_fee_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.merchant_fee_assessment
    SELECT * FROM staging.merchant_fee_assessment
    WHERE batch_id = @batch_id
END
GO
