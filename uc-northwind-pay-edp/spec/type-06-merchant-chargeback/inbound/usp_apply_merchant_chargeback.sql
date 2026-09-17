-- legacy.apply_merchant_chargeback_batch  dump 2026-07-18
CREATE PROCEDURE legacy.apply_merchant_chargeback_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.merchant_chargeback
    SELECT * FROM staging.merchant_chargeback
    WHERE batch_id = @batch_id
END
GO
