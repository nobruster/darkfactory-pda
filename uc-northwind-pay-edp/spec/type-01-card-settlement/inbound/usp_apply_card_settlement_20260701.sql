-- usp_apply_card_settlement  -- dumped 2026-07-01
-- Rafael: "use this one. May dump still has the May script, ignore it."
CREATE PROCEDURE legacy.apply_card_settlement_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.card_settlement
    SELECT s.*
    FROM staging.card_settlement s
    WHERE s.batch_id = @batch_id
      AND NOT EXISTS (
          SELECT 1 FROM legacy.card_settlement l
          WHERE l.batch_id = s.batch_id
            AND l.source_record_number = s.source_record_number
      )
END
GO
-- refunds (R, negative overpunch) are first-class
-- chargeback_flag is not populated
