\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS staging.ted_transfer_movement (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL CHECK (
        source_file ~
        '^NW_TED_SETTLEMENT_[0-9]{8}_B[0-9]{15}\.dat$'
    ),
    source_record_number integer NOT NULL CHECK (
        source_record_number >= 2
        AND source_record_number <= 20001
    ),
    movement_id text NOT NULL CHECK (
        movement_id ~ '^[A-Z][A-Z0-9]{15}$'
    ),
    original_transfer_id text CHECK (
        original_transfer_id ~ '^[A-Z][A-Z0-9]{15}$'
    ),
    movement_kind text NOT NULL CHECK (
        movement_kind IN ('TRANSFER', 'RETURN')
    ),
    movement_ts text NOT NULL CHECK (
        movement_ts ~
        '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}$'
    ),
    amount_brl numeric(16, 2) NOT NULL CHECK (amount_brl <> 0),
    payer_account_token text NOT NULL CHECK (
        payer_account_token ~ '^tedacct_[0-9a-f]{24}$'
    ),
    payer_tax_id_masked text NOT NULL CHECK (
        payer_tax_id_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    beneficiary_account_token text NOT NULL CHECK (
        beneficiary_account_token ~ '^tedacct_[0-9a-f]{24}$'
    ),
    beneficiary_tax_id_masked text NOT NULL CHECK (
        beneficiary_tax_id_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    beneficiary_ispb text NOT NULL CHECK (
        beneficiary_ispb ~ '^[0-9]{8}$'
    ),
    purpose_code text NOT NULL CHECK (
        purpose_code ~ '^[A-Z][A-Z0-9_]{1,9}$'
    ),
    status_code text NOT NULL CHECK (status_code IN ('OK', 'RT')),
    return_reason_code text CHECK (
        return_reason_code ~ '^[A-Z][A-Z0-9]{4}$'
    ),
    PRIMARY KEY (batch_id, movement_id),
    UNIQUE (batch_id, source_record_number),
    CHECK (
        (
            movement_kind = 'TRANSFER'
            AND original_transfer_id IS NULL
            AND amount_brl > 0
            AND return_reason_code IS NULL
        )
        OR (
            movement_kind = 'RETURN'
            AND original_transfer_id IS NOT NULL
            AND amount_brl < 0
            AND status_code = 'RT'
            AND return_reason_code IS NOT NULL
        )
    )
);

CREATE TABLE IF NOT EXISTS legacy.ted_transfer_movement (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number integer NOT NULL,
    movement_id text NOT NULL CHECK (
        movement_id ~ '^[A-Z][A-Z0-9]{15}$'
    ),
    original_transfer_id text,
    movement_kind text NOT NULL CHECK (
        movement_kind IN ('TRANSFER', 'RETURN')
    ),
    movement_ts text NOT NULL,
    amount_brl numeric(16, 2) NOT NULL,
    payer_account_token text NOT NULL CHECK (
        payer_account_token ~ '^tedacct_[0-9a-f]{24}$'
    ),
    payer_tax_id_masked text NOT NULL CHECK (
        payer_tax_id_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    beneficiary_account_token text NOT NULL CHECK (
        beneficiary_account_token ~ '^tedacct_[0-9a-f]{24}$'
    ),
    beneficiary_tax_id_masked text NOT NULL CHECK (
        beneficiary_tax_id_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    beneficiary_ispb text NOT NULL,
    purpose_code text NOT NULL,
    status_code text NOT NULL CHECK (status_code IN ('OK', 'RT')),
    return_reason_code text,
    PRIMARY KEY (batch_id, movement_id),
    UNIQUE (batch_id, source_record_number),
    UNIQUE (movement_id)
);

CREATE TABLE IF NOT EXISTS reporting.ted_transfer_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_transfer_count integer NOT NULL,
    staged_transfer_count integer NOT NULL,
    applied_transfer_count integer NOT NULL,
    source_return_count integer NOT NULL,
    staged_return_count integer NOT NULL,
    applied_return_count integer NOT NULL,
    source_gross_amount numeric(16, 2) NOT NULL,
    staged_gross_amount numeric(16, 2) NOT NULL,
    applied_gross_amount numeric(16, 2) NOT NULL,
    source_return_amount numeric(16, 2) NOT NULL,
    staged_return_amount numeric(16, 2) NOT NULL,
    applied_return_amount numeric(16, 2) NOT NULL,
    source_net_amount numeric(16, 2) NOT NULL,
    staged_net_amount numeric(16, 2) NOT NULL,
    applied_net_amount numeric(16, 2) NOT NULL,
    transfer_count_delta integer NOT NULL,
    return_count_delta integer NOT NULL,
    gross_amount_delta numeric(16, 2) NOT NULL,
    return_amount_delta numeric(16, 2) NOT NULL,
    net_amount_delta numeric(16, 2) NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);

CREATE OR REPLACE FUNCTION legacy.apply_ted_transfer_batch(
    p_batch_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    controls jsonb;
    expected_count integer;
    applied_count integer;
BEGIN
    SELECT source_controls
      INTO STRICT controls
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '04';

    expected_count :=
        (controls ->> 'transfer_count')::integer
        + (controls ->> 'return_count')::integer;

    INSERT INTO legacy.ted_transfer_movement (
        batch_id,
        source_file,
        source_record_number,
        movement_id,
        original_transfer_id,
        movement_kind,
        movement_ts,
        amount_brl,
        payer_account_token,
        payer_tax_id_masked,
        beneficiary_account_token,
        beneficiary_tax_id_masked,
        beneficiary_ispb,
        purpose_code,
        status_code,
        return_reason_code
    )
    SELECT
        batch_id,
        source_file,
        source_record_number,
        movement_id,
        original_transfer_id,
        movement_kind,
        movement_ts,
        amount_brl,
        payer_account_token,
        payer_tax_id_masked,
        beneficiary_account_token,
        beneficiary_tax_id_masked,
        beneficiary_ispb,
        purpose_code,
        status_code,
        return_reason_code
      FROM staging.ted_transfer_movement
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, movement_id) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.ted_transfer_movement
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied Type 04 count does not match source controls'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number,
                movement_id,
                original_transfer_id,
                movement_kind,
                movement_ts,
                amount_brl,
                payer_account_token,
                payer_tax_id_masked,
                beneficiary_account_token,
                beneficiary_tax_id_masked,
                beneficiary_ispb,
                purpose_code,
                status_code,
                return_reason_code
              FROM staging.ted_transfer_movement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                movement_id,
                original_transfer_id,
                movement_kind,
                movement_ts,
                amount_brl,
                payer_account_token,
                payer_tax_id_masked,
                beneficiary_account_token,
                beneficiary_tax_id_masked,
                beneficiary_ispb,
                purpose_code,
                status_code,
                return_reason_code
              FROM legacy.ted_transfer_movement
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number,
                movement_id,
                original_transfer_id,
                movement_kind,
                movement_ts,
                amount_brl,
                payer_account_token,
                payer_tax_id_masked,
                beneficiary_account_token,
                beneficiary_tax_id_masked,
                beneficiary_ispb,
                purpose_code,
                status_code,
                return_reason_code
              FROM legacy.ted_transfer_movement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                movement_id,
                original_transfer_id,
                movement_kind,
                movement_ts,
                amount_brl,
                payer_account_token,
                payer_tax_id_masked,
                beneficiary_account_token,
                beneficiary_tax_id_masked,
                beneficiary_ispb,
                purpose_code,
                status_code,
                return_reason_code
              FROM staging.ted_transfer_movement
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied Type 04 rows differ from immutable staging'
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
        'legacy.apply_ted_transfer_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION
reporting.refresh_ted_transfer_reconciliation(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    controls jsonb;
    source_transfer_count integer;
    source_return_count integer;
    source_gross numeric(16, 2);
    source_return numeric(16, 2);
    source_net numeric(16, 2);
    staged_transfer_count integer;
    staged_return_count integer;
    staged_gross numeric(16, 2);
    staged_return numeric(16, 2);
    staged_net numeric(16, 2);
    applied_transfer_count integer;
    applied_return_count integer;
    applied_gross numeric(16, 2);
    applied_return numeric(16, 2);
    applied_net numeric(16, 2);
    rejected integer;
BEGIN
    SELECT source_controls
      INTO STRICT controls
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '04';

    source_transfer_count :=
        (controls ->> 'transfer_count')::integer;
    source_return_count :=
        (controls ->> 'return_count')::integer;
    source_gross := (controls ->> 'gross_amount')::numeric;
    source_return := (controls ->> 'return_amount')::numeric;
    source_net := (controls ->> 'net_amount')::numeric;

    SELECT
        count(*) FILTER (WHERE movement_kind = 'TRANSFER'),
        count(*) FILTER (WHERE movement_kind = 'RETURN'),
        coalesce(
            sum(amount_brl) FILTER (WHERE movement_kind = 'TRANSFER'),
            0.00
        ),
        coalesce(
            sum(amount_brl) FILTER (WHERE movement_kind = 'RETURN'),
            0.00
        ),
        coalesce(sum(amount_brl), 0.00)
      INTO
        staged_transfer_count,
        staged_return_count,
        staged_gross,
        staged_return,
        staged_net
      FROM staging.ted_transfer_movement
     WHERE batch_id = p_batch_id;

    SELECT
        count(*) FILTER (WHERE movement_kind = 'TRANSFER'),
        count(*) FILTER (WHERE movement_kind = 'RETURN'),
        coalesce(
            sum(amount_brl) FILTER (WHERE movement_kind = 'TRANSFER'),
            0.00
        ),
        coalesce(
            sum(amount_brl) FILTER (WHERE movement_kind = 'RETURN'),
            0.00
        ),
        coalesce(sum(amount_brl), 0.00)
      INTO
        applied_transfer_count,
        applied_return_count,
        applied_gross,
        applied_return,
        applied_net
      FROM legacy.ted_transfer_movement
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO rejected
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    INSERT INTO reporting.ted_transfer_reconciliation (
        batch_id,
        currency,
        source_transfer_count,
        staged_transfer_count,
        applied_transfer_count,
        source_return_count,
        staged_return_count,
        applied_return_count,
        source_gross_amount,
        staged_gross_amount,
        applied_gross_amount,
        source_return_amount,
        staged_return_amount,
        applied_return_amount,
        source_net_amount,
        staged_net_amount,
        applied_net_amount,
        transfer_count_delta,
        return_count_delta,
        gross_amount_delta,
        return_amount_delta,
        net_amount_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        source_transfer_count,
        staged_transfer_count,
        applied_transfer_count,
        source_return_count,
        staged_return_count,
        applied_return_count,
        source_gross,
        staged_gross,
        applied_gross,
        source_return,
        staged_return,
        applied_return,
        source_net,
        staged_net,
        applied_net,
        applied_transfer_count - source_transfer_count,
        applied_return_count - source_return_count,
        applied_gross - source_gross,
        applied_return - source_return,
        applied_net - source_net,
        rejected,
        CASE
            WHEN source_transfer_count = staged_transfer_count
             AND source_transfer_count = applied_transfer_count
             AND source_return_count = staged_return_count
             AND source_return_count = applied_return_count
             AND source_gross = staged_gross
             AND source_gross = applied_gross
             AND source_return = staged_return
             AND source_return = applied_return
             AND source_net = staged_net
             AND source_net = applied_net
             AND rejected = 0
            THEN 'MATCHED'
            ELSE 'MISMATCHED'
        END
    )
    ON CONFLICT (batch_id, currency) DO UPDATE
       SET source_transfer_count = excluded.source_transfer_count,
           staged_transfer_count = excluded.staged_transfer_count,
           applied_transfer_count = excluded.applied_transfer_count,
           source_return_count = excluded.source_return_count,
           staged_return_count = excluded.staged_return_count,
           applied_return_count = excluded.applied_return_count,
           source_gross_amount = excluded.source_gross_amount,
           staged_gross_amount = excluded.staged_gross_amount,
           applied_gross_amount = excluded.applied_gross_amount,
           source_return_amount = excluded.source_return_amount,
           staged_return_amount = excluded.staged_return_amount,
           applied_return_amount = excluded.applied_return_amount,
           source_net_amount = excluded.source_net_amount,
           staged_net_amount = excluded.staged_net_amount,
           applied_net_amount = excluded.applied_net_amount,
           transfer_count_delta = excluded.transfer_count_delta,
           return_count_delta = excluded.return_count_delta,
           gross_amount_delta = excluded.gross_amount_delta,
           return_amount_delta = excluded.return_amount_delta,
           net_amount_delta = excluded.net_amount_delta,
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
        'reporting.refresh_ted_transfer_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

COMMENT ON TABLE staging.ted_transfer_movement IS
'Privacy-safe Type 04 transfer and return movements loaded through COPY.';

COMMENT ON FUNCTION legacy.apply_ted_transfer_batch(text) IS
'Idempotently applies immutable Type 04 movements and rejects row drift.';

COMMENT ON FUNCTION
reporting.refresh_ted_transfer_reconciliation(text) IS
'Recomputes zero-tolerance Type 04 signed movement controls.';

ALTER TABLE staging.ted_transfer_movement
    OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.ted_transfer_movement
    OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.ted_transfer_reconciliation
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_ted_transfer_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION reporting.refresh_ted_transfer_reconciliation(text)
    OWNER TO northwind_legacy_owner;

REVOKE ALL ON staging.ted_transfer_movement FROM PUBLIC;
REVOKE ALL ON legacy.ted_transfer_movement FROM PUBLIC;
REVOKE ALL ON reporting.ted_transfer_reconciliation FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
legacy.apply_ted_transfer_batch(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
reporting.refresh_ted_transfer_reconciliation(text) FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON staging.ted_transfer_movement TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT SELECT ON legacy.ted_transfer_movement, '
        'reporting.ted_transfer_reconciliation TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'legacy.apply_ted_transfer_batch(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'reporting.refresh_ted_transfer_reconciliation(text) TO %I',
        app_user
    );
END;
$$;
