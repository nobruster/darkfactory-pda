\set ON_ERROR_STOP on

ALTER TABLE control.batches
    DROP CONSTRAINT IF EXISTS batches_file_type_check;

ALTER TABLE control.batches
    ADD CONSTRAINT batches_file_type_check CHECK (
        file_type IN ('01', '02', '03', '04', '05', '06')
    );

CREATE TABLE IF NOT EXISTS staging.merchant_chargeback (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL CHECK (
        source_file ~
        '^NW_MERCHANT_CHARGEBACK_[0-9]{8}_B[0-9]{15}\.csv$'
    ),
    source_record_number integer NOT NULL CHECK (
        source_record_number >= 2
        AND source_record_number <= 10001
    ),
    chargeback_id text NOT NULL CHECK (
        chargeback_id ~ '^CBK[0-9]{13}$'
    ),
    merchant_id text NOT NULL CHECK (
        merchant_id ~ '^MER[0-9]{13}$'
    ),
    merchant_tax_id_masked text NOT NULL CHECK (
        merchant_tax_id_masked ~ '^\*{10}[0-9]{4}$'
    ),
    reason_code text NOT NULL CHECK (
        reason_code ~ '^[A-Z][A-Z0-9_]{1,9}$'
    ),
    description text NOT NULL CHECK (
        char_length(description) BETWEEN 1 AND 80
        AND description !~ '[[:cntrl:]]'
        AND description !~ '^[=+@-]'
        AND description !~ '[0-9]{11}'
    ),
    original_amount_brl numeric(14, 2) NOT NULL CHECK (
        original_amount_brl > 0
    ),
    rate_percent numeric(6, 3) NOT NULL CHECK (
        rate_percent > 0
        AND rate_percent <= 100
    ),
    chargeback_amount_brl numeric(14, 2) NOT NULL CHECK (
        chargeback_amount_brl >= 0
    ),
    calculated_amount_brl numeric(14, 2) NOT NULL CHECK (
        calculated_amount_brl >= 0
    ),
    business_date date NOT NULL,
    rounding_mode text NOT NULL CHECK (rounding_mode = 'HALF_EVEN'),
    PRIMARY KEY (batch_id, chargeback_id),
    UNIQUE (batch_id, source_record_number),
    CHECK (chargeback_amount_brl = calculated_amount_brl)
);

CREATE TABLE IF NOT EXISTS legacy.merchant_chargeback (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number integer NOT NULL,
    chargeback_id text NOT NULL CHECK (
        chargeback_id ~ '^CBK[0-9]{13}$'
    ),
    merchant_id text NOT NULL CHECK (
        merchant_id ~ '^MER[0-9]{13}$'
    ),
    merchant_tax_id_masked text NOT NULL CHECK (
        merchant_tax_id_masked ~ '^\*{10}[0-9]{4}$'
    ),
    reason_code text NOT NULL,
    description text NOT NULL,
    original_amount_brl numeric(14, 2) NOT NULL,
    rate_percent numeric(6, 3) NOT NULL,
    chargeback_amount_brl numeric(14, 2) NOT NULL,
    calculated_amount_brl numeric(14, 2) NOT NULL,
    business_date date NOT NULL,
    rounding_mode text NOT NULL CHECK (rounding_mode = 'HALF_EVEN'),
    PRIMARY KEY (batch_id, chargeback_id),
    UNIQUE (batch_id, source_record_number),
    UNIQUE (chargeback_id)
);

CREATE TABLE IF NOT EXISTS reporting.merchant_chargeback_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_count integer NOT NULL,
    staged_count integer NOT NULL,
    applied_count integer NOT NULL,
    source_original_amount numeric(18, 2) NOT NULL,
    staged_original_amount numeric(18, 2) NOT NULL,
    applied_original_amount numeric(18, 2) NOT NULL,
    source_chargeback_amount numeric(18, 2) NOT NULL,
    staged_chargeback_amount numeric(18, 2) NOT NULL,
    applied_chargeback_amount numeric(18, 2) NOT NULL,
    source_calculated_amount numeric(18, 2) NOT NULL,
    staged_calculated_amount numeric(18, 2) NOT NULL,
    applied_calculated_amount numeric(18, 2) NOT NULL,
    count_delta integer NOT NULL,
    original_amount_delta numeric(18, 2) NOT NULL,
    chargeback_amount_delta numeric(18, 2) NOT NULL,
    calculated_amount_delta numeric(18, 2) NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);

CREATE OR REPLACE FUNCTION
legacy.apply_merchant_chargeback_batch(p_batch_id text)
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
       AND file_type = '06';

    INSERT INTO legacy.merchant_chargeback (
        batch_id,
        source_file,
        source_record_number,
        chargeback_id,
        merchant_id,
        merchant_tax_id_masked,
        reason_code,
        description,
        original_amount_brl,
        rate_percent,
        chargeback_amount_brl,
        calculated_amount_brl,
        business_date,
        rounding_mode
    )
    SELECT
        batch_id,
        source_file,
        source_record_number,
        chargeback_id,
        merchant_id,
        merchant_tax_id_masked,
        reason_code,
        description,
        original_amount_brl,
        rate_percent,
        chargeback_amount_brl,
        calculated_amount_brl,
        business_date,
        rounding_mode
      FROM staging.merchant_chargeback
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, chargeback_id) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.merchant_chargeback
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied Type 06 count does not match the source control'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number,
                chargeback_id,
                merchant_id,
                merchant_tax_id_masked,
                reason_code,
                description,
                original_amount_brl,
                rate_percent,
                chargeback_amount_brl,
                calculated_amount_brl,
                business_date,
                rounding_mode
              FROM staging.merchant_chargeback
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                chargeback_id,
                merchant_id,
                merchant_tax_id_masked,
                reason_code,
                description,
                original_amount_brl,
                rate_percent,
                chargeback_amount_brl,
                calculated_amount_brl,
                business_date,
                rounding_mode
              FROM legacy.merchant_chargeback
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number,
                chargeback_id,
                merchant_id,
                merchant_tax_id_masked,
                reason_code,
                description,
                original_amount_brl,
                rate_percent,
                chargeback_amount_brl,
                calculated_amount_brl,
                business_date,
                rounding_mode
              FROM legacy.merchant_chargeback
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                chargeback_id,
                merchant_id,
                merchant_tax_id_masked,
                reason_code,
                description,
                original_amount_brl,
                rate_percent,
                chargeback_amount_brl,
                calculated_amount_brl,
                business_date,
                rounding_mode
              FROM staging.merchant_chargeback
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied Type 06 rows differ from immutable staging'
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
        'legacy.apply_merchant_chargeback_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION
reporting.refresh_merchant_chargeback_reconciliation(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    staged_count integer;
    staged_original numeric(18, 2);
    staged_chargeback numeric(18, 2);
    staged_calculated numeric(18, 2);
    applied_count integer;
    applied_original numeric(18, 2);
    applied_chargeback numeric(18, 2);
    applied_calculated numeric(18, 2);
    rejected integer;
BEGIN
    PERFORM 1
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '06';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Type 06 batch is not registered'
            USING ERRCODE = 'P0001';
    END IF;

    SELECT
        count(*),
        coalesce(sum(original_amount_brl), 0.00),
        coalesce(sum(chargeback_amount_brl), 0.00),
        coalesce(sum(calculated_amount_brl), 0.00)
      INTO
        staged_count,
        staged_original,
        staged_chargeback,
        staged_calculated
      FROM staging.merchant_chargeback
     WHERE batch_id = p_batch_id;

    SELECT
        count(*),
        coalesce(sum(original_amount_brl), 0.00),
        coalesce(sum(chargeback_amount_brl), 0.00),
        coalesce(sum(calculated_amount_brl), 0.00)
      INTO
        applied_count,
        applied_original,
        applied_chargeback,
        applied_calculated
      FROM legacy.merchant_chargeback
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO rejected
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    INSERT INTO reporting.merchant_chargeback_reconciliation (
        batch_id,
        currency,
        source_count,
        staged_count,
        applied_count,
        source_original_amount,
        staged_original_amount,
        applied_original_amount,
        source_chargeback_amount,
        staged_chargeback_amount,
        applied_chargeback_amount,
        source_calculated_amount,
        staged_calculated_amount,
        applied_calculated_amount,
        count_delta,
        original_amount_delta,
        chargeback_amount_delta,
        calculated_amount_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        staged_count,
        staged_count,
        applied_count,
        staged_original,
        staged_original,
        applied_original,
        staged_chargeback,
        staged_chargeback,
        applied_chargeback,
        staged_calculated,
        staged_calculated,
        applied_calculated,
        applied_count - staged_count,
        applied_original - staged_original,
        applied_chargeback - staged_chargeback,
        applied_calculated - staged_calculated,
        rejected,
        CASE
            WHEN staged_count = applied_count
             AND staged_original = applied_original
             AND staged_chargeback = applied_chargeback
             AND staged_calculated = applied_calculated
             AND staged_chargeback = staged_calculated
             AND rejected = 0
            THEN 'MATCHED'
            ELSE 'MISMATCHED'
        END
    )
    ON CONFLICT (batch_id, currency) DO UPDATE
       SET source_count = excluded.source_count,
           staged_count = excluded.staged_count,
           applied_count = excluded.applied_count,
           source_original_amount = excluded.source_original_amount,
           staged_original_amount = excluded.staged_original_amount,
           applied_original_amount = excluded.applied_original_amount,
           source_chargeback_amount = excluded.source_chargeback_amount,
           staged_chargeback_amount = excluded.staged_chargeback_amount,
           applied_chargeback_amount = excluded.applied_chargeback_amount,
           source_calculated_amount = excluded.source_calculated_amount,
           staged_calculated_amount = excluded.staged_calculated_amount,
           applied_calculated_amount = excluded.applied_calculated_amount,
           count_delta = excluded.count_delta,
           original_amount_delta = excluded.original_amount_delta,
           chargeback_amount_delta = excluded.chargeback_amount_delta,
           calculated_amount_delta = excluded.calculated_amount_delta,
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
        'reporting.refresh_merchant_chargeback_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION control.register_batch_v2(
    p_batch_id text,
    p_file_type text,
    p_source_filename text,
    p_source_sha256 text,
    p_source_manifest_sha256 text,
    p_source_controls jsonb,
    p_source_count integer,
    p_source_net_amount numeric,
    p_status text,
    p_failure_code text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    observed record;
    controls_count integer;
    controls_compatibility_amount numeric;
BEGIN
    IF p_file_type NOT IN ('01', '02', '03', '04', '05', '06')
       OR jsonb_typeof(p_source_controls) <> 'object' THEN
        RAISE EXCEPTION 'Unsafe file type or source control map'
            USING ERRCODE = '22023';
    END IF;
    IF p_status NOT IN ('claimed', 'quarantined', 'oracle_mismatch') THEN
        RAISE EXCEPTION 'Unsafe initial batch status'
            USING ERRCODE = '22023';
    END IF;
    IF (p_status = 'claimed' AND p_failure_code IS NOT NULL)
       OR (p_status <> 'claimed' AND p_failure_code IS NULL) THEN
        RAISE EXCEPTION 'Failure code does not match initial batch status'
            USING ERRCODE = '22023';
    END IF;

    BEGIN
        controls_count := coalesce(
            (p_source_controls ->> 'detail_count')::integer,
            (p_source_controls ->> 'event_count')::integer,
            (p_source_controls ->> 'logical_count')::integer,
            (p_source_controls ->> 'transfer_count')::integer,
            (p_source_controls ->> 'assessment_count')::integer,
            (p_source_controls ->> 'row_count')::integer
        );
        controls_compatibility_amount := coalesce(
            (p_source_controls ->> 'net_amount')::numeric,
            (p_source_controls ->> 'assessed_fee')::numeric,
            (p_source_controls ->> 'chargeback_amount')::numeric
        );
    EXCEPTION
        WHEN invalid_text_representation OR numeric_value_out_of_range THEN
            RAISE EXCEPTION 'Source control map is not canonical'
                USING ERRCODE = '22023';
    END;
    IF controls_count IS DISTINCT FROM p_source_count
       OR controls_compatibility_amount
            IS DISTINCT FROM p_source_net_amount THEN
        RAISE EXCEPTION 'Compatibility controls disagree with source map'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO control.batches (
        batch_id,
        file_type,
        source_filename,
        source_sha256,
        source_manifest_sha256,
        source_count,
        source_net_amount,
        source_controls,
        status,
        failure_code
    )
    VALUES (
        p_batch_id,
        p_file_type,
        p_source_filename,
        p_source_sha256,
        p_source_manifest_sha256,
        p_source_count,
        p_source_net_amount,
        p_source_controls,
        p_status,
        p_failure_code
    )
    ON CONFLICT (batch_id) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.batches
     WHERE batch_id = p_batch_id;
    IF observed.file_type <> p_file_type
       OR observed.source_filename <> p_source_filename
       OR observed.source_sha256 <> p_source_sha256
       OR observed.source_manifest_sha256 <> p_source_manifest_sha256
       OR observed.source_count <> p_source_count
       OR observed.source_net_amount <> p_source_net_amount
       OR observed.source_controls <> p_source_controls
       OR NOT (
           (
               p_status = 'claimed'
               AND observed.status IN (
                   'claimed',
                   'database_committed_pending_archive',
                   'succeeded'
               )
               AND observed.failure_code IS NULL
           )
           OR (
               p_status <> 'claimed'
               AND observed.status = p_status
               AND observed.failure_code IS NOT DISTINCT FROM p_failure_code
           )
       ) THEN
        RAISE EXCEPTION 'Batch identity or state changed on replay'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

COMMENT ON TABLE staging.merchant_chargeback IS
'Privacy-safe Type 06 chargebacks loaded from a verified normalized CSV.';

COMMENT ON FUNCTION
legacy.apply_merchant_chargeback_batch(text) IS
'Idempotently applies immutable Type 06 chargeback rows and rejects row drift.';

COMMENT ON FUNCTION
reporting.refresh_merchant_chargeback_reconciliation(text) IS
'Recomputes Type 06 controls using staged amounts as the source projection.';

COMMENT ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) IS
'Registers immutable source identity and complete type controls. The legacy '
'compatibility amount is net for Types 01-04, assessed fee for Type 05, and '
'chargeback amount for Type 06.';

ALTER TABLE staging.merchant_chargeback
    OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.merchant_chargeback
    OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.merchant_chargeback_reconciliation
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_merchant_chargeback_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION reporting.refresh_merchant_chargeback_reconciliation(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) OWNER TO northwind_legacy_owner;

REVOKE ALL ON staging.merchant_chargeback FROM PUBLIC;
REVOKE ALL ON legacy.merchant_chargeback FROM PUBLIC;
REVOKE ALL ON reporting.merchant_chargeback_reconciliation FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
legacy.apply_merchant_chargeback_batch(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
reporting.refresh_merchant_chargeback_reconciliation(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON staging.merchant_chargeback TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT SELECT ON legacy.merchant_chargeback, '
        'reporting.merchant_chargeback_reconciliation TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'legacy.apply_merchant_chargeback_batch(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'reporting.refresh_merchant_chargeback_reconciliation(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION control.register_batch_v2('
        'text, text, text, text, text, jsonb, integer, numeric, text, text'
        ') TO %I',
        app_user
    );
END;
$$;
