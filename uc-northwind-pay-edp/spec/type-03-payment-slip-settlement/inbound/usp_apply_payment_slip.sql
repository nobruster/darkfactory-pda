-- legacy.apply_payment_slip_batch  dump 2026-06-22
-- does not write lot_remark
CREATE PROCEDURE legacy.apply_payment_slip_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.payment_slip_settlement
    SELECT batch_id, source_record_number, lot_number,
           payment_ref_token, beneficiary_token, account_token,
           document_masked, face_amount, discount_amount, fee_amount, net_amount
    FROM staging.payment_slip_settlement
    WHERE batch_id = @batch_id
END
GO
