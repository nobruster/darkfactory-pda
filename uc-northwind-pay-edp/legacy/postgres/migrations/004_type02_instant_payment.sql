\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS staging.instant_payment_event (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL CHECK (
        source_file ~
        '^NW_INSTANT_PAYMENT_[0-9]{8}_B[0-9]{15}\.txt$'
    ),
    source_record_number integer NOT NULL CHECK (
        source_record_number > 1
    ),
    end_to_end_id text NOT NULL CHECK (
        end_to_end_id ~ '^E[0-9]{31}$'
    ),
    transaction_id text NOT NULL CHECK (
        transaction_id ~ '^[A-Z0-9]{16}$'
        AND transaction_id ~ '[A-Z]'
    ),
    payer_document_token text NOT NULL CHECK (
        payer_document_token ~ '^doc_[0-9a-f]{24}$'
    ),
    payer_document_masked text NOT NULL CHECK (
        payer_document_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    payee_document_token text NOT NULL CHECK (
        payee_document_token ~ '^doc_[0-9a-f]{24}$'
    ),
    payee_document_masked text NOT NULL CHECK (
        payee_document_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    event_timestamp text NOT NULL CHECK (
        event_timestamp ~
        '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$'
        AND event_timestamp !~ '[+-]00:00$'
    ),
    amount_brl numeric(18, 2) NOT NULL,
    direction text NOT NULL CHECK (direction IN ('C', 'D')),
    status text NOT NULL CHECK (status IN ('SETTLED', 'RETURNED')),
    return_code text,
    description text NOT NULL CHECK (
        description <> ''
        AND description !~ '[[:cntrl:]]'
        AND description !~ '^[=+@-]'
        AND description !~ '[0-9]{11}'
    ),
    PRIMARY KEY (batch_id, source_record_number),
    UNIQUE (batch_id, end_to_end_id),
    UNIQUE (batch_id, transaction_id),
    CHECK (
        (direction = 'C' AND amount_brl > 0)
        OR (direction = 'D' AND amount_brl < 0)
    ),
    CHECK (
        (status = 'SETTLED' AND return_code IS NULL)
        OR (
            status = 'RETURNED'
            AND return_code ~ '^[A-Z0-9]{1,4}$'
        )
    )
);

CREATE TABLE IF NOT EXISTS legacy.instant_payment_event (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number integer NOT NULL,
    end_to_end_id text NOT NULL
        CHECK (end_to_end_id ~ '^E[0-9]{31}$'),
    transaction_id text NOT NULL,
    payer_document_token text NOT NULL
        CHECK (payer_document_token ~ '^doc_[0-9a-f]{24}$'),
    payer_document_masked text NOT NULL
        CHECK (payer_document_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'),
    payee_document_token text NOT NULL
        CHECK (payee_document_token ~ '^doc_[0-9a-f]{24}$'),
    payee_document_masked text NOT NULL
        CHECK (payee_document_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'),
    event_timestamp text NOT NULL,
    amount_brl numeric(18, 2) NOT NULL,
    direction text NOT NULL CHECK (direction IN ('C', 'D')),
    status text NOT NULL CHECK (status IN ('SETTLED', 'RETURNED')),
    return_code text,
    description text NOT NULL,
    PRIMARY KEY (batch_id, source_record_number),
    UNIQUE (batch_id, end_to_end_id),
    UNIQUE (batch_id, transaction_id),
    UNIQUE (end_to_end_id)
);

CREATE TABLE IF NOT EXISTS reporting.instant_payment_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_count integer NOT NULL,
    staged_count integer NOT NULL,
    applied_count integer NOT NULL,
    source_credit_amount numeric(18, 2) NOT NULL,
    staged_credit_amount numeric(18, 2) NOT NULL,
    applied_credit_amount numeric(18, 2) NOT NULL,
    source_debit_amount numeric(18, 2) NOT NULL,
    staged_debit_amount numeric(18, 2) NOT NULL,
    applied_debit_amount numeric(18, 2) NOT NULL,
    source_net_amount numeric(18, 2) NOT NULL,
    staged_net_amount numeric(18, 2) NOT NULL,
    applied_net_amount numeric(18, 2) NOT NULL,
    source_returned_count integer NOT NULL,
    staged_returned_count integer NOT NULL,
    applied_returned_count integer NOT NULL,
    count_delta integer NOT NULL,
    credit_amount_delta numeric(18, 2) NOT NULL,
    debit_amount_delta numeric(18, 2) NOT NULL,
    net_amount_delta numeric(18, 2) NOT NULL,
    returned_count_delta integer NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);

CREATE OR REPLACE FUNCTION legacy.apply_instant_payment_batch(
    p_batch_id text
)
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
     WHERE batch_id = p_batch_id
       AND file_type = '02';

    INSERT INTO legacy.instant_payment_event (
        batch_id,
        source_file,
        source_record_number,
        end_to_end_id,
        transaction_id,
        payer_document_token,
        payer_document_masked,
        payee_document_token,
        payee_document_masked,
        event_timestamp,
        amount_brl,
        direction,
        status,
        return_code,
        description
    )
    SELECT
        batch_id,
        source_file,
        source_record_number,
        end_to_end_id,
        transaction_id,
        payer_document_token,
        payer_document_masked,
        payee_document_token,
        payee_document_masked,
        event_timestamp,
        amount_brl,
        direction,
        status,
        return_code,
        description
      FROM staging.instant_payment_event
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, source_record_number) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.instant_payment_event
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied Type 02 count does not match the source control'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                amount_brl,
                direction,
                status,
                return_code,
                description
              FROM staging.instant_payment_event
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                amount_brl,
                direction,
                status,
                return_code,
                description
              FROM legacy.instant_payment_event
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                amount_brl,
                direction,
                status,
                return_code,
                description
              FROM legacy.instant_payment_event
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                amount_brl,
                direction,
                status,
                return_code,
                description
              FROM staging.instant_payment_event
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied Type 02 rows differ from immutable staging'
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
        'legacy.apply_instant_payment_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION
reporting.refresh_instant_payment_reconciliation(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    source_controls jsonb;
    stage_controls jsonb;
    source_count integer;
    source_credit numeric(18, 2);
    source_debit numeric(18, 2);
    source_net numeric(18, 2);
    source_returned integer;
    staged_count integer;
    staged_credit numeric(18, 2);
    staged_debit numeric(18, 2);
    staged_net numeric(18, 2);
    staged_returned integer;
    applied_count integer;
    applied_credit numeric(18, 2);
    applied_debit numeric(18, 2);
    applied_net numeric(18, 2);
    applied_returned integer;
    rejected integer;
BEGIN
    SELECT batch.source_controls, load.stage_controls
      INTO STRICT source_controls, stage_controls
      FROM control.batches AS batch
      JOIN control.loads AS load USING (batch_id)
     WHERE batch.batch_id = p_batch_id
       AND batch.file_type = '02';

    source_count := (source_controls ->> 'event_count')::integer;
    source_credit := (source_controls ->> 'credit_amount')::numeric;
    source_debit := (source_controls ->> 'debit_amount')::numeric;
    source_net := (source_controls ->> 'net_amount')::numeric;
    source_returned := (stage_controls ->> 'returned_count')::integer;

    SELECT
        count(*),
        coalesce(sum(amount_brl) FILTER (WHERE direction = 'C'), 0.00),
        coalesce(sum(abs(amount_brl)) FILTER (WHERE direction = 'D'), 0.00),
        coalesce(sum(amount_brl), 0.00),
        count(*) FILTER (WHERE status = 'RETURNED')
      INTO
        staged_count,
        staged_credit,
        staged_debit,
        staged_net,
        staged_returned
      FROM staging.instant_payment_event
     WHERE batch_id = p_batch_id;

    SELECT
        count(*),
        coalesce(sum(amount_brl) FILTER (WHERE direction = 'C'), 0.00),
        coalesce(sum(abs(amount_brl)) FILTER (WHERE direction = 'D'), 0.00),
        coalesce(sum(amount_brl), 0.00),
        count(*) FILTER (WHERE status = 'RETURNED')
      INTO
        applied_count,
        applied_credit,
        applied_debit,
        applied_net,
        applied_returned
      FROM legacy.instant_payment_event
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO rejected
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    INSERT INTO reporting.instant_payment_reconciliation (
        batch_id,
        currency,
        source_count,
        staged_count,
        applied_count,
        source_credit_amount,
        staged_credit_amount,
        applied_credit_amount,
        source_debit_amount,
        staged_debit_amount,
        applied_debit_amount,
        source_net_amount,
        staged_net_amount,
        applied_net_amount,
        source_returned_count,
        staged_returned_count,
        applied_returned_count,
        count_delta,
        credit_amount_delta,
        debit_amount_delta,
        net_amount_delta,
        returned_count_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        source_count,
        staged_count,
        applied_count,
        source_credit,
        staged_credit,
        applied_credit,
        source_debit,
        staged_debit,
        applied_debit,
        source_net,
        staged_net,
        applied_net,
        source_returned,
        staged_returned,
        applied_returned,
        applied_count - source_count,
        applied_credit - source_credit,
        applied_debit - source_debit,
        applied_net - source_net,
        applied_returned - source_returned,
        rejected,
        CASE
            WHEN source_count = staged_count
             AND source_count = applied_count
             AND source_credit = staged_credit
             AND source_credit = applied_credit
             AND source_debit = staged_debit
             AND source_debit = applied_debit
             AND source_net = staged_net
             AND source_net = applied_net
             AND source_returned = staged_returned
             AND source_returned = applied_returned
             AND rejected = 0
            THEN 'MATCHED'
            ELSE 'MISMATCHED'
        END
    )
    ON CONFLICT (batch_id, currency) DO UPDATE
       SET source_count = excluded.source_count,
           staged_count = excluded.staged_count,
           applied_count = excluded.applied_count,
           source_credit_amount = excluded.source_credit_amount,
           staged_credit_amount = excluded.staged_credit_amount,
           applied_credit_amount = excluded.applied_credit_amount,
           source_debit_amount = excluded.source_debit_amount,
           staged_debit_amount = excluded.staged_debit_amount,
           applied_debit_amount = excluded.applied_debit_amount,
           source_net_amount = excluded.source_net_amount,
           staged_net_amount = excluded.staged_net_amount,
           applied_net_amount = excluded.applied_net_amount,
           source_returned_count = excluded.source_returned_count,
           staged_returned_count = excluded.staged_returned_count,
           applied_returned_count = excluded.applied_returned_count,
           count_delta = excluded.count_delta,
           credit_amount_delta = excluded.credit_amount_delta,
           debit_amount_delta = excluded.debit_amount_delta,
           net_amount_delta = excluded.net_amount_delta,
           returned_count_delta = excluded.returned_count_delta,
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
        'reporting.refresh_instant_payment_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

COMMENT ON TABLE staging.instant_payment_event IS
'Privacy-safe Type 02 rows loaded from a verified sanitized CSV through COPY.';

COMMENT ON FUNCTION legacy.apply_instant_payment_batch(text) IS
'Idempotently copies immutable Type 02 staging rows into the operational '
'table inside the loader transaction and refuses row drift.';

COMMENT ON FUNCTION
reporting.refresh_instant_payment_reconciliation(text) IS
'Recomputes zero-tolerance Type 02 source, staging, operational, and return '
'controls inside the loader transaction.';

ALTER TABLE staging.instant_payment_event
    OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.instant_payment_event
    OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.instant_payment_reconciliation
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_instant_payment_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION reporting.refresh_instant_payment_reconciliation(text)
    OWNER TO northwind_legacy_owner;

REVOKE ALL ON staging.instant_payment_event FROM PUBLIC;
REVOKE ALL ON legacy.instant_payment_event FROM PUBLIC;
REVOKE ALL ON reporting.instant_payment_reconciliation FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION legacy.apply_instant_payment_batch(text)
    FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
reporting.refresh_instant_payment_reconciliation(text)
    FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON staging.instant_payment_event TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT SELECT ON legacy.instant_payment_event, '
        'reporting.instant_payment_reconciliation TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'legacy.apply_instant_payment_batch(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'reporting.refresh_instant_payment_reconciliation(text) TO %I',
        app_user
    );
END;
$$;
