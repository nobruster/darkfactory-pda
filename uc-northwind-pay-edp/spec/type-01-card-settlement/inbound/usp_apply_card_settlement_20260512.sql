-- usp_apply_card_settlement  -- dumped 2026-05-12
-- Rafael: "this is the one from before we had refunds on the same file"
CREATE PROCEDURE legacy.apply_card_settlement_batch @batch_id char(16)
AS
BEGIN
    -- copies staging rows where amount_brl > 0 only
    INSERT INTO legacy.card_settlement
    SELECT * FROM staging.card_settlement
    WHERE batch_id = @batch_id
      AND amount_brl > 0
END
GO
-- NOTE: negative-overpunch / refunds were not in this revision
