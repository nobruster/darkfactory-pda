\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS staging.merchant_fee_assessment (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL CHECK (
        source_file ~
        '^NW_MERCHANT_FEES_[0-9]{8}_B[0-9]{15}\.csv$'
    ),
    source_record_number integer NOT NULL CHECK (
        source_record_number >= 2
        AND source_record_number <= 10001
    ),
    assessment_id text NOT NULL CHECK (
        assessment_id ~ '^FEE[0-9]{13}$'
    ),
    merchant_id text NOT NULL CHECK (
        merchant_id ~ '^MER[0-9]{13}$'
    ),
    merchant_tax_id_masked text NOT NULL CHECK (
        merchant_tax_id_masked ~ '^\*{10}[0-9]{4}$'
    ),
    fee_code text NOT NULL CHECK (
        fee_code ~ '^[A-Z][A-Z0-9_]{1,9}$'
    ),
    description text NOT NULL CHECK (
        char_length(description) BETWEEN 1 AND 80
        AND description !~ '[[:cntrl:]]'
        AND description !~ '^[=+@-]'
        AND description !~ '[0-9]{11}'
    ),
    gross_amount_brl numeric(14, 2) NOT NULL CHECK (
        gross_amount_brl > 0
    ),
    rate_percent numeric(6, 3) NOT NULL CHECK (
        rate_percent > 0
        AND rate_percent <= 100
    ),
    assessed_fee_brl numeric(14, 2) NOT NULL CHECK (
        assessed_fee_brl >= 0
    ),
    calculated_fee_brl numeric(14, 2) NOT NULL CHECK (
        calculated_fee_brl >= 0
    ),
    assessment_date date NOT NULL,
    rounding_mode text NOT NULL CHECK (rounding_mode = 'HALF_UP'),
    PRIMARY KEY (batch_id, assessment_id),
    UNIQUE (batch_id, source_record_number),
    CHECK (assessed_fee_brl = calculated_fee_brl)
);

CREATE TABLE IF NOT EXISTS legacy.merchant_fee_assessment (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number integer NOT NULL,
    assessment_id text NOT NULL CHECK (
        assessment_id ~ '^FEE[0-9]{13}$'
    ),
    merchant_id text NOT NULL CHECK (
        merchant_id ~ '^MER[0-9]{13}$'
    ),
    merchant_tax_id_masked text NOT NULL CHECK (
        merchant_tax_id_masked ~ '^\*{10}[0-9]{4}$'
    ),
    fee_code text NOT NULL,
    description text NOT NULL,
    gross_amount_brl numeric(14, 2) NOT NULL,
    rate_percent numeric(6, 3) NOT NULL,
    assessed_fee_brl numeric(14, 2) NOT NULL,
    calculated_fee_brl numeric(14, 2) NOT NULL,
    assessment_date date NOT NULL,
    rounding_mode text NOT NULL CHECK (rounding_mode = 'HALF_UP'),
    PRIMARY KEY (batch_id, assessment_id),
    UNIQUE (batch_id, source_record_number),
    UNIQUE (assessment_id)
);

CREATE TABLE IF NOT EXISTS reporting.merchant_fee_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_count integer NOT NULL,
    staged_count integer NOT NULL,
    applied_count integer NOT NULL,
    source_gross_amount numeric(14, 2) NOT NULL,
    staged_gross_amount numeric(14, 2) NOT NULL,
    applied_gross_amount numeric(14, 2) NOT NULL,
    source_assessed_fee numeric(14, 2) NOT NULL,
    staged_assessed_fee numeric(14, 2) NOT NULL,
    applied_assessed_fee numeric(14, 2) NOT NULL,
    source_calculated_fee numeric(14, 2) NOT NULL,
    staged_calculated_fee numeric(14, 2) NOT NULL,
    applied_calculated_fee numeric(14, 2) NOT NULL,
    count_delta integer NOT NULL,
    gross_amount_delta numeric(14, 2) NOT NULL,
    assessed_fee_delta numeric(14, 2) NOT NULL,
    calculated_fee_delta numeric(14, 2) NOT NULL,
    assessment_calculation_delta numeric(14, 2) NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);

CREATE OR REPLACE FUNCTION
legacy.apply_merchant_fee_assessment_batch(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    expected_count integer;
    applied_count integer;
BEGIN
    SELECT (source_controls ->> 'row_count')::integer
      INTO STRICT expected_count
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '05';

    INSERT INTO legacy.merchant_fee_assessment (
        batch_id,
        source_file,
        source_record_number,
        assessment_id,
        merchant_id,
        merchant_tax_id_masked,
        fee_code,
        description,
        gross_amount_brl,
        rate_percent,
        assessed_fee_brl,
        calculated_fee_brl,
        assessment_date,
        rounding_mode
    )
    SELECT
        batch_id,
        source_file,
        source_record_number,
        assessment_id,
        merchant_id,
        merchant_tax_id_masked,
        fee_code,
        description,
        gross_amount_brl,
        rate_percent,
        assessed_fee_brl,
        calculated_fee_brl,
        assessment_date,
        rounding_mode
      FROM staging.merchant_fee_assessment
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, assessment_id) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.merchant_fee_assessment
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied Type 05 count does not match the source control'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number,
                assessment_id,
                merchant_id,
                merchant_tax_id_masked,
                fee_code,
                description,
                gross_amount_brl,
                rate_percent,
                assessed_fee_brl,
                calculated_fee_brl,
                assessment_date,
                rounding_mode
              FROM staging.merchant_fee_assessment
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                assessment_id,
                merchant_id,
                merchant_tax_id_masked,
                fee_code,
                description,
                gross_amount_brl,
                rate_percent,
                assessed_fee_brl,
                calculated_fee_brl,
                assessment_date,
                rounding_mode
              FROM legacy.merchant_fee_assessment
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number,
                assessment_id,
                merchant_id,
                merchant_tax_id_masked,
                fee_code,
                description,
                gross_amount_brl,
                rate_percent,
                assessed_fee_brl,
                calculated_fee_brl,
                assessment_date,
                rounding_mode
              FROM legacy.merchant_fee_assessment
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                assessment_id,
                merchant_id,
                merchant_tax_id_masked,
                fee_code,
                description,
                gross_amount_brl,
                rate_percent,
                assessed_fee_brl,
                calculated_fee_brl,
                assessment_date,
                rounding_mode
              FROM staging.merchant_fee_assessment
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied Type 05 rows differ from immutable staging'
            USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO control.procedure_runs (
        batch_id,
        sequence_number,
        procedure_name,
        status
    )
    VALUES (
        p_batch_id,
        1,
        'legacy.apply_merchant_fee_assessment_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

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
    source_gross numeric(14, 2);
    source_assessed numeric(14, 2);
    source_calculated numeric(14, 2);
    staged_count integer;
    staged_gross numeric(14, 2);
    staged_assessed numeric(14, 2);
    staged_calculated numeric(14, 2);
    applied_count integer;
    applied_gross numeric(14, 2);
    applied_assessed numeric(14, 2);
    applied_calculated numeric(14, 2);
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

COMMENT ON TABLE staging.merchant_fee_assessment IS
'Privacy-safe Type 05 fee assessments loaded from a verified normalized CSV.';

COMMENT ON FUNCTION
legacy.apply_merchant_fee_assessment_batch(text) IS
'Idempotently applies immutable Type 05 fee rows and rejects row drift.';

COMMENT ON FUNCTION
reporting.refresh_merchant_fee_reconciliation(text) IS
'Recomputes zero-tolerance Type 05 source, stage, operational, and fee controls.';

ALTER TABLE staging.merchant_fee_assessment
    OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.merchant_fee_assessment
    OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.merchant_fee_reconciliation
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_merchant_fee_assessment_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION reporting.refresh_merchant_fee_reconciliation(text)
    OWNER TO northwind_legacy_owner;

REVOKE ALL ON staging.merchant_fee_assessment FROM PUBLIC;
REVOKE ALL ON legacy.merchant_fee_assessment FROM PUBLIC;
REVOKE ALL ON reporting.merchant_fee_reconciliation FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
legacy.apply_merchant_fee_assessment_batch(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
reporting.refresh_merchant_fee_reconciliation(text) FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON staging.merchant_fee_assessment TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT SELECT ON legacy.merchant_fee_assessment, '
        'reporting.merchant_fee_reconciliation TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'legacy.apply_merchant_fee_assessment_batch(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'reporting.refresh_merchant_fee_reconciliation(text) TO %I',
        app_user
    );
END;
$$;
