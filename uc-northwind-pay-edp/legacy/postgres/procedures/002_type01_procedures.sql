\set ON_ERROR_STOP on

CREATE OR REPLACE FUNCTION control.register_batch(
    p_batch_id text,
    p_source_filename text,
    p_source_sha256 text,
    p_source_manifest_sha256 text,
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
BEGIN
    IF p_status NOT IN ('claimed', 'quarantined', 'oracle_mismatch') THEN
        RAISE EXCEPTION 'Unsafe initial batch status'
            USING ERRCODE = '22023';
    END IF;
    IF (p_status = 'claimed' AND p_failure_code IS NOT NULL)
       OR (p_status <> 'claimed' AND p_failure_code IS NULL) THEN
        RAISE EXCEPTION 'Failure code does not match initial batch status'
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
        status,
        failure_code
    )
    VALUES (
        p_batch_id,
        '01',
        p_source_filename,
        p_source_sha256,
        p_source_manifest_sha256,
        p_source_count,
        p_source_net_amount,
        p_status,
        p_failure_code
    )
    ON CONFLICT (batch_id) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.batches
     WHERE batch_id = p_batch_id;
    IF observed.file_type <> '01'
       OR observed.source_filename <> p_source_filename
       OR observed.source_sha256 <> p_source_sha256
       OR observed.source_manifest_sha256 <> p_source_manifest_sha256
       OR observed.source_count <> p_source_count
       OR observed.source_net_amount <> p_source_net_amount
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

CREATE OR REPLACE FUNCTION control.register_file(
    p_batch_id text,
    p_stage text,
    p_filename text,
    p_sha256 text,
    p_size_bytes bigint
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    observed record;
BEGIN
    INSERT INTO control.files (
        batch_id, stage, filename, sha256, size_bytes
    )
    VALUES (
        p_batch_id, p_stage, p_filename, p_sha256, p_size_bytes
    )
    ON CONFLICT (batch_id, stage) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.files
     WHERE batch_id = p_batch_id
       AND stage = p_stage;
    IF observed.filename <> p_filename
       OR observed.sha256 <> p_sha256
       OR observed.size_bytes <> p_size_bytes THEN
        RAISE EXCEPTION 'File identity changed on replay'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION control.register_load(
    p_batch_id text,
    p_staged_count integer,
    p_staged_net_amount numeric
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    observed record;
BEGIN
    INSERT INTO control.loads (
        batch_id, staged_count, staged_net_amount, status
    )
    VALUES (
        p_batch_id, p_staged_count, p_staged_net_amount, 'loaded'
    )
    ON CONFLICT (batch_id) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.loads
     WHERE batch_id = p_batch_id;
    IF observed.staged_count <> p_staged_count
       OR observed.staged_net_amount <> p_staged_net_amount
       OR observed.status <> 'loaded' THEN
        RAISE EXCEPTION 'Load controls changed on replay'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION control.register_reject(
    p_batch_id text,
    p_stage text,
    p_code text,
    p_computed_count integer,
    p_computed_net_amount numeric,
    p_declared_count integer,
    p_declared_net_amount numeric
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    observed record;
BEGIN
    INSERT INTO control.rejects (
        batch_id,
        stage,
        code,
        computed_count,
        computed_net_amount,
        declared_count,
        declared_net_amount
    )
    VALUES (
        p_batch_id,
        p_stage,
        p_code,
        p_computed_count,
        p_computed_net_amount,
        p_declared_count,
        p_declared_net_amount
    )
    ON CONFLICT (batch_id, stage, code) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.rejects
     WHERE batch_id = p_batch_id
       AND stage = p_stage
       AND code = p_code;
    IF observed.computed_count IS DISTINCT FROM p_computed_count
       OR observed.computed_net_amount
            IS DISTINCT FROM p_computed_net_amount
       OR observed.declared_count IS DISTINCT FROM p_declared_count
       OR observed.declared_net_amount
            IS DISTINCT FROM p_declared_net_amount THEN
        RAISE EXCEPTION 'Reject controls changed on replay'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION control.mark_batch_committed(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    UPDATE control.batches
       SET status = CASE
               WHEN status = 'succeeded' THEN 'succeeded'
               ELSE 'database_committed_pending_archive'
           END,
           failure_code = NULL
     WHERE batch_id = p_batch_id
       AND status IN (
           'claimed',
           'database_committed_pending_archive',
           'succeeded'
       )
       AND failure_code IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Batch cannot transition to committed'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION control.mark_batch_succeeded(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    UPDATE control.batches
       SET status = 'succeeded',
           failure_code = NULL
     WHERE batch_id = p_batch_id
       AND status IN (
           'database_committed_pending_archive',
           'succeeded'
       )
       AND failure_code IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Batch cannot transition to succeeded'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION legacy.apply_card_settlement_batch(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    expected_count integer;
    applied_count integer;
BEGIN
    SELECT source_count
      INTO STRICT expected_count
      FROM control.batches
     WHERE batch_id = p_batch_id;

    INSERT INTO legacy.card_settlement (
        batch_id,
        source_file,
        source_record_number,
        transaction_id,
        merchant_id,
        card_token,
        card_last4,
        cpf_masked,
        transaction_ts,
        amount_brl,
        movement_code,
        authorization_code,
        nsu,
        terminal_id
    )
    SELECT
        batch_id,
        source_file,
        source_record_number,
        transaction_id,
        merchant_id,
        card_token,
        card_last4,
        cpf_masked,
        transaction_ts,
        amount_brl,
        movement_code,
        authorization_code,
        nsu,
        terminal_id
      FROM staging.card_settlement
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, source_record_number) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.card_settlement
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied count does not match the batch source control'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number,
                transaction_id,
                merchant_id,
                card_token,
                card_last4,
                cpf_masked,
                transaction_ts,
                amount_brl,
                movement_code,
                authorization_code,
                nsu,
                terminal_id
              FROM staging.card_settlement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                transaction_id,
                merchant_id,
                card_token,
                card_last4,
                cpf_masked,
                transaction_ts,
                amount_brl,
                movement_code,
                authorization_code,
                nsu,
                terminal_id
              FROM legacy.card_settlement
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number,
                transaction_id,
                merchant_id,
                card_token,
                card_last4,
                cpf_masked,
                transaction_ts,
                amount_brl,
                movement_code,
                authorization_code,
                nsu,
                terminal_id
              FROM legacy.card_settlement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                transaction_id,
                merchant_id,
                card_token,
                card_last4,
                cpf_masked,
                transaction_ts,
                amount_brl,
                movement_code,
                authorization_code,
                nsu,
                terminal_id
              FROM staging.card_settlement
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied rows do not match the immutable staging rows'
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
        'legacy.apply_card_settlement_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name)
    DO UPDATE SET
        sequence_number = EXCLUDED.sequence_number,
        status = EXCLUDED.status;
END;
$$;

CREATE OR REPLACE FUNCTION
reporting.refresh_card_settlement_reconciliation(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    source_count_value integer;
    staged_count_value integer;
    applied_count_value integer;
    reject_count_value integer;
    source_net_value numeric(18, 2);
    staged_net_value numeric(18, 2);
    applied_net_value numeric(18, 2);
    count_delta_value integer;
    amount_delta_value numeric(18, 2);
    status_value text;
BEGIN
    SELECT source_count, source_net_amount
      INTO STRICT source_count_value, source_net_value
      FROM control.batches
     WHERE batch_id = p_batch_id;

    SELECT count(*), coalesce(sum(amount_brl), 0.00)
      INTO staged_count_value, staged_net_value
      FROM staging.card_settlement
     WHERE batch_id = p_batch_id;

    SELECT count(*), coalesce(sum(amount_brl), 0.00)
      INTO applied_count_value, applied_net_value
      FROM legacy.card_settlement
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO reject_count_value
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    count_delta_value := applied_count_value - source_count_value;
    amount_delta_value := applied_net_value - source_net_value;
    status_value := CASE
        WHEN source_count_value = staged_count_value
         AND source_count_value = applied_count_value
         AND source_net_value = staged_net_value
         AND source_net_value = applied_net_value
         AND reject_count_value = 0
        THEN 'MATCHED'
        ELSE 'MISMATCHED'
    END;

    INSERT INTO reporting.card_settlement_reconciliation (
        batch_id,
        currency,
        source_count,
        staged_count,
        applied_count,
        source_net_amount,
        staged_net_amount,
        applied_net_amount,
        count_delta,
        amount_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        source_count_value,
        staged_count_value,
        applied_count_value,
        source_net_value,
        staged_net_value,
        applied_net_value,
        count_delta_value,
        amount_delta_value,
        reject_count_value,
        status_value
    )
    ON CONFLICT (batch_id, currency)
    DO UPDATE SET
        source_count = EXCLUDED.source_count,
        staged_count = EXCLUDED.staged_count,
        applied_count = EXCLUDED.applied_count,
        source_net_amount = EXCLUDED.source_net_amount,
        staged_net_amount = EXCLUDED.staged_net_amount,
        applied_net_amount = EXCLUDED.applied_net_amount,
        count_delta = EXCLUDED.count_delta,
        amount_delta = EXCLUDED.amount_delta,
        reject_count = EXCLUDED.reject_count,
        status = EXCLUDED.status;

    INSERT INTO control.procedure_runs (
        batch_id,
        sequence_number,
        procedure_name,
        status
    )
    VALUES (
        p_batch_id,
        2,
        'reporting.refresh_card_settlement_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name)
    DO UPDATE SET
        sequence_number = EXCLUDED.sequence_number,
        status = EXCLUDED.status;
END;
$$;
