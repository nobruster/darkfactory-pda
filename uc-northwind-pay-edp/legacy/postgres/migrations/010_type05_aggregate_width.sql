\set ON_ERROR_STOP on

ALTER TABLE reporting.merchant_fee_reconciliation
    ALTER COLUMN source_gross_amount TYPE numeric(18, 2),
    ALTER COLUMN staged_gross_amount TYPE numeric(18, 2),
    ALTER COLUMN applied_gross_amount TYPE numeric(18, 2),
    ALTER COLUMN source_assessed_fee TYPE numeric(18, 2),
    ALTER COLUMN staged_assessed_fee TYPE numeric(18, 2),
    ALTER COLUMN applied_assessed_fee TYPE numeric(18, 2),
    ALTER COLUMN source_calculated_fee TYPE numeric(18, 2),
    ALTER COLUMN staged_calculated_fee TYPE numeric(18, 2),
    ALTER COLUMN applied_calculated_fee TYPE numeric(18, 2),
    ALTER COLUMN gross_amount_delta TYPE numeric(18, 2),
    ALTER COLUMN assessed_fee_delta TYPE numeric(18, 2),
    ALTER COLUMN calculated_fee_delta TYPE numeric(18, 2),
    ALTER COLUMN assessment_calculation_delta TYPE numeric(18, 2);

CREATE OR REPLACE FUNCTION
reporting.refresh_merchant_fee_reconciliation(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    controls jsonb;
    source_count integer;
    source_gross numeric(18, 2);
    source_assessed numeric(18, 2);
    source_calculated numeric(18, 2);
    staged_count integer;
    staged_gross numeric(18, 2);
    staged_assessed numeric(18, 2);
    staged_calculated numeric(18, 2);
    applied_count integer;
    applied_gross numeric(18, 2);
    applied_assessed numeric(18, 2);
    applied_calculated numeric(18, 2);
    rejected integer;
BEGIN
    SELECT source_controls
      INTO STRICT controls
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '05';

    source_count := (controls ->> 'row_count')::integer;
    source_gross := (controls ->> 'gross_amount')::numeric;
    source_assessed := (controls ->> 'assessed_fee')::numeric;
    source_calculated := (controls ->> 'calculated_fee')::numeric;

    SELECT
        count(*),
        coalesce(sum(gross_amount_brl), 0.00),
        coalesce(sum(assessed_fee_brl), 0.00),
        coalesce(sum(calculated_fee_brl), 0.00)
      INTO
        staged_count,
        staged_gross,
        staged_assessed,
        staged_calculated
      FROM staging.merchant_fee_assessment
     WHERE batch_id = p_batch_id;

    SELECT
        count(*),
        coalesce(sum(gross_amount_brl), 0.00),
        coalesce(sum(assessed_fee_brl), 0.00),
        coalesce(sum(calculated_fee_brl), 0.00)
      INTO
        applied_count,
        applied_gross,
        applied_assessed,
        applied_calculated
      FROM legacy.merchant_fee_assessment
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO rejected
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    INSERT INTO reporting.merchant_fee_reconciliation (
        batch_id,
        currency,
        source_count,
        staged_count,
        applied_count,
        source_gross_amount,
        staged_gross_amount,
        applied_gross_amount,
        source_assessed_fee,
        staged_assessed_fee,
        applied_assessed_fee,
        source_calculated_fee,
        staged_calculated_fee,
        applied_calculated_fee,
        count_delta,
        gross_amount_delta,
        assessed_fee_delta,
        calculated_fee_delta,
        assessment_calculation_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        source_count,
        staged_count,
        applied_count,
        source_gross,
        staged_gross,
        applied_gross,
        source_assessed,
        staged_assessed,
        applied_assessed,
        source_calculated,
        staged_calculated,
        applied_calculated,
        applied_count - source_count,
        applied_gross - source_gross,
        applied_assessed - source_assessed,
        applied_calculated - source_calculated,
        applied_assessed - applied_calculated,
        rejected,
        CASE
            WHEN source_count = staged_count
             AND source_count = applied_count
             AND source_gross = staged_gross
             AND source_gross = applied_gross
             AND source_assessed = staged_assessed
             AND source_assessed = applied_assessed
             AND source_calculated = staged_calculated
             AND source_calculated = applied_calculated
             AND applied_assessed = applied_calculated
             AND rejected = 0
            THEN 'MATCHED'
            ELSE 'MISMATCHED'
        END
    )
    ON CONFLICT (batch_id, currency) DO UPDATE
       SET source_count = excluded.source_count,
           staged_count = excluded.staged_count,
           applied_count = excluded.applied_count,
           source_gross_amount = excluded.source_gross_amount,
           staged_gross_amount = excluded.staged_gross_amount,
           applied_gross_amount = excluded.applied_gross_amount,
           source_assessed_fee = excluded.source_assessed_fee,
           staged_assessed_fee = excluded.staged_assessed_fee,
           applied_assessed_fee = excluded.applied_assessed_fee,
           source_calculated_fee = excluded.source_calculated_fee,
           staged_calculated_fee = excluded.staged_calculated_fee,
           applied_calculated_fee = excluded.applied_calculated_fee,
           count_delta = excluded.count_delta,
           gross_amount_delta = excluded.gross_amount_delta,
           assessed_fee_delta = excluded.assessed_fee_delta,
           calculated_fee_delta = excluded.calculated_fee_delta,
           assessment_calculation_delta =
               excluded.assessment_calculation_delta,
           reject_count = excluded.reject_count,
           status = excluded.status;

    INSERT INTO control.procedure_runs (
        batch_id,
        sequence_number,
        procedure_name,
        status
    )
    VALUES (
        p_batch_id,
        2,
        'reporting.refresh_merchant_fee_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

COMMENT ON FUNCTION
reporting.refresh_merchant_fee_reconciliation(text) IS
'Recomputes Type 05 controls with batch-width monetary aggregates.';
