-- dump 2026-04-18  — transfers only, ignored returns
CREATE PROCEDURE legacy.apply_ted_transfer_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.ted_transfer_movement
    SELECT * FROM staging.ted_transfer_movement
    WHERE batch_id = @batch_id
      AND movement_kind = 'TRANSFER'
END
GO
