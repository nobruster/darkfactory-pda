-- legacy.apply_instant_payment_batch
-- dump 2026-06-21. Does not touch event_memo.
CREATE PROCEDURE legacy.apply_instant_payment_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.instant_payment_event
    SELECT batch_id, source_record_number, event_id, direction, amount_brl,
           payer_doc_token, payer_doc_masked, payee_doc_token, payee_doc_masked,
           event_ts, status, return_code, description
    FROM staging.instant_payment_event
    WHERE batch_id = @batch_id
END
GO
