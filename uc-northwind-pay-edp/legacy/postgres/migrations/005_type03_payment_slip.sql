\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS staging.payment_slip_settlement (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL CHECK (
        source_file ~
        '^NW_PAYMENT_SLIP_[0-9]{8}_B[0-9]{15}\.rem$'
    ),
    source_record_number_a integer NOT NULL CHECK (
        source_record_number_a >= 3
        AND source_record_number_a <= 22000
    ),
    source_record_number_b integer NOT NULL CHECK (
        source_record_number_b >= 4
        AND source_record_number_b <= 22001
    ),
    lot_number text NOT NULL CHECK (
        lot_number ~ '^(?!000000)[0-9]{6}$'
    ),
    sequence text NOT NULL CHECK (
        sequence ~ '^(?!000000)[0-9]{6}$'
    ),
    settlement_id text NOT NULL CHECK (
        settlement_id ~ '^[A-Z][A-Z0-9]{15}$'
    ),
    payment_reference_token text NOT NULL CHECK (
        payment_reference_token ~ '^payref_[0-9a-f]{24}$'
    ),
    payment_reference_last4 text NOT NULL CHECK (
        payment_reference_last4 ~ '^[0-9]{4}$'
    ),
    beneficiary_token text NOT NULL CHECK (
        beneficiary_token ~ '^party_[0-9a-f]{24}$'
    ),
    beneficiary_tax_id_type text NOT NULL CHECK (
        beneficiary_tax_id_type IN ('CPF', 'CNPJ')
    ),
    beneficiary_tax_id_masked text NOT NULL CHECK (
        (
            beneficiary_tax_id_type = 'CPF'
            AND beneficiary_tax_id_masked ~ '^\*{7}[0-9]{4}$'
        )
        OR (
            beneficiary_tax_id_type = 'CNPJ'
            AND beneficiary_tax_id_masked ~ '^\*{10}[0-9]{4}$'
        )
    ),
    bank_account_token text NOT NULL CHECK (
        bank_account_token ~ '^acct_[0-9a-f]{24}$'
    ),
    bank_account_last4 text NOT NULL CHECK (
        bank_account_last4 ~ '^[0-9]{4}$'
    ),
    due_date date NOT NULL,
    payment_date date NOT NULL,
    face_amount_brl numeric(18, 2) NOT NULL CHECK (
        face_amount_brl > 0
    ),
    discount_brl numeric(18, 2) NOT NULL CHECK (
        discount_brl >= 0
    ),
    fee_brl numeric(18, 2) NOT NULL CHECK (
        fee_brl >= 0
    ),
    net_amount_brl numeric(18, 2) NOT NULL CHECK (
        net_amount_brl >= 0
    ),
    status text NOT NULL CHECK (status = 'SETTLED'),
    bank_reference text NOT NULL CHECK (
        bank_reference ~ '^[A-Z][A-Z0-9]{19}$'
    ),
    client_reference text NOT NULL CHECK (
        client_reference ~ '^[A-Z][A-Z0-9]{19}$'
    ),
    PRIMARY KEY (batch_id, lot_number, sequence),
    UNIQUE (batch_id, settlement_id),
    CHECK (source_record_number_b = source_record_number_a + 1),
    CHECK (payment_date <= due_date),
    CHECK (discount_brl <= face_amount_brl),
    CHECK (
        net_amount_brl = face_amount_brl - discount_brl + fee_brl
    )
);

CREATE TABLE IF NOT EXISTS legacy.payment_slip_settlement (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number_a integer NOT NULL,
    source_record_number_b integer NOT NULL,
    lot_number text NOT NULL,
    sequence text NOT NULL,
    settlement_id text NOT NULL CHECK (
        settlement_id ~ '^[A-Z][A-Z0-9]{15}$'
    ),
    payment_reference_token text NOT NULL CHECK (
        payment_reference_token ~ '^payref_[0-9a-f]{24}$'
    ),
    payment_reference_last4 text NOT NULL CHECK (
        payment_reference_last4 ~ '^[0-9]{4}$'
    ),
    beneficiary_token text NOT NULL CHECK (
        beneficiary_token ~ '^party_[0-9a-f]{24}$'
    ),
    beneficiary_tax_id_type text NOT NULL CHECK (
        beneficiary_tax_id_type IN ('CPF', 'CNPJ')
    ),
    beneficiary_tax_id_masked text NOT NULL CHECK (
        beneficiary_tax_id_masked ~ '^(\*{7}|\*{10})[0-9]{4}$'
    ),
    bank_account_token text NOT NULL CHECK (
        bank_account_token ~ '^acct_[0-9a-f]{24}$'
    ),
    bank_account_last4 text NOT NULL CHECK (
        bank_account_last4 ~ '^[0-9]{4}$'
    ),
    due_date date NOT NULL,
    payment_date date NOT NULL,
    face_amount_brl numeric(18, 2) NOT NULL,
    discount_brl numeric(18, 2) NOT NULL,
    fee_brl numeric(18, 2) NOT NULL,
    net_amount_brl numeric(18, 2) NOT NULL,
    status text NOT NULL CHECK (status = 'SETTLED'),
    bank_reference text NOT NULL,
    client_reference text NOT NULL,
    PRIMARY KEY (batch_id, lot_number, sequence),
    UNIQUE (batch_id, settlement_id),
    UNIQUE (settlement_id)
);

CREATE TABLE IF NOT EXISTS
reporting.payment_slip_settlement_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_count integer NOT NULL,
    staged_count integer NOT NULL,
    applied_count integer NOT NULL,
    source_face_amount numeric(18, 2) NOT NULL,
    staged_face_amount numeric(18, 2) NOT NULL,
    applied_face_amount numeric(18, 2) NOT NULL,
    source_discount_amount numeric(18, 2) NOT NULL,
    staged_discount_amount numeric(18, 2) NOT NULL,
    applied_discount_amount numeric(18, 2) NOT NULL,
    source_fee_amount numeric(18, 2) NOT NULL,
    staged_fee_amount numeric(18, 2) NOT NULL,
    applied_fee_amount numeric(18, 2) NOT NULL,
    source_net_amount numeric(18, 2) NOT NULL,
    staged_net_amount numeric(18, 2) NOT NULL,
    applied_net_amount numeric(18, 2) NOT NULL,
    source_orphan_segment_count integer NOT NULL,
    staged_orphan_segment_count integer NOT NULL,
    applied_orphan_segment_count integer NOT NULL,
    count_delta integer NOT NULL,
    face_amount_delta numeric(18, 2) NOT NULL,
    discount_amount_delta numeric(18, 2) NOT NULL,
    fee_amount_delta numeric(18, 2) NOT NULL,
    net_amount_delta numeric(18, 2) NOT NULL,
    orphan_segment_count_delta integer NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);

CREATE OR REPLACE FUNCTION
legacy.apply_payment_slip_settlement_batch(p_batch_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    expected_count integer;
    applied_count integer;
BEGIN
    SELECT (source_controls ->> 'logical_count')::integer
      INTO STRICT expected_count
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '03';

    INSERT INTO legacy.payment_slip_settlement (
        batch_id,
        source_file,
        source_record_number_a,
        source_record_number_b,
        lot_number,
        sequence,
        settlement_id,
        payment_reference_token,
        payment_reference_last4,
        beneficiary_token,
        beneficiary_tax_id_type,
        beneficiary_tax_id_masked,
        bank_account_token,
        bank_account_last4,
        due_date,
        payment_date,
        face_amount_brl,
        discount_brl,
        fee_brl,
        net_amount_brl,
        status,
        bank_reference,
        client_reference
    )
    SELECT
        batch_id,
        source_file,
        source_record_number_a,
        source_record_number_b,
        lot_number,
        sequence,
        settlement_id,
        payment_reference_token,
        payment_reference_last4,
        beneficiary_token,
        beneficiary_tax_id_type,
        beneficiary_tax_id_masked,
        bank_account_token,
        bank_account_last4,
        due_date,
        payment_date,
        face_amount_brl,
        discount_brl,
        fee_brl,
        net_amount_brl,
        status,
        bank_reference,
        client_reference
      FROM staging.payment_slip_settlement
     WHERE batch_id = p_batch_id
    ON CONFLICT (batch_id, lot_number, sequence) DO NOTHING;

    SELECT count(*)
      INTO applied_count
      FROM legacy.payment_slip_settlement
     WHERE batch_id = p_batch_id;

    IF applied_count <> expected_count THEN
        RAISE EXCEPTION
            'Applied Type 03 count does not match the source control'
            USING ERRCODE = 'P0001';
    END IF;

    IF EXISTS (
        (
            SELECT
                source_file,
                source_record_number_a,
                source_record_number_b,
                lot_number,
                sequence,
                settlement_id,
                payment_reference_token,
                payment_reference_last4,
                beneficiary_token,
                beneficiary_tax_id_type,
                beneficiary_tax_id_masked,
                bank_account_token,
                bank_account_last4,
                due_date,
                payment_date,
                face_amount_brl,
                discount_brl,
                fee_brl,
                net_amount_brl,
                status,
                bank_reference,
                client_reference
              FROM staging.payment_slip_settlement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number_a,
                source_record_number_b,
                lot_number,
                sequence,
                settlement_id,
                payment_reference_token,
                payment_reference_last4,
                beneficiary_token,
                beneficiary_tax_id_type,
                beneficiary_tax_id_masked,
                bank_account_token,
                bank_account_last4,
                due_date,
                payment_date,
                face_amount_brl,
                discount_brl,
                fee_brl,
                net_amount_brl,
                status,
                bank_reference,
                client_reference
              FROM legacy.payment_slip_settlement
             WHERE batch_id = p_batch_id
        )
        UNION ALL
        (
            SELECT
                source_file,
                source_record_number_a,
                source_record_number_b,
                lot_number,
                sequence,
                settlement_id,
                payment_reference_token,
                payment_reference_last4,
                beneficiary_token,
                beneficiary_tax_id_type,
                beneficiary_tax_id_masked,
                bank_account_token,
                bank_account_last4,
                due_date,
                payment_date,
                face_amount_brl,
                discount_brl,
                fee_brl,
                net_amount_brl,
                status,
                bank_reference,
                client_reference
              FROM legacy.payment_slip_settlement
             WHERE batch_id = p_batch_id
            EXCEPT
            SELECT
                source_file,
                source_record_number_a,
                source_record_number_b,
                lot_number,
                sequence,
                settlement_id,
                payment_reference_token,
                payment_reference_last4,
                beneficiary_token,
                beneficiary_tax_id_type,
                beneficiary_tax_id_masked,
                bank_account_token,
                bank_account_last4,
                due_date,
                payment_date,
                face_amount_brl,
                discount_brl,
                fee_brl,
                net_amount_brl,
                status,
                bank_reference,
                client_reference
              FROM staging.payment_slip_settlement
             WHERE batch_id = p_batch_id
        )
    ) THEN
        RAISE EXCEPTION
            'Applied Type 03 rows differ from immutable staging'
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
        'legacy.apply_payment_slip_settlement_batch',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION
reporting.refresh_payment_slip_settlement_reconciliation(
    p_batch_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    controls jsonb;
    source_count integer;
    source_face numeric(18, 2);
    source_discount numeric(18, 2);
    source_fee numeric(18, 2);
    source_net numeric(18, 2);
    source_orphans integer;
    staged_count integer;
    staged_face numeric(18, 2);
    staged_discount numeric(18, 2);
    staged_fee numeric(18, 2);
    staged_net numeric(18, 2);
    applied_count integer;
    applied_face numeric(18, 2);
    applied_discount numeric(18, 2);
    applied_fee numeric(18, 2);
    applied_net numeric(18, 2);
    rejected integer;
BEGIN
    SELECT source_controls
      INTO STRICT controls
      FROM control.batches
     WHERE batch_id = p_batch_id
       AND file_type = '03';

    source_count := (controls ->> 'logical_count')::integer;
    source_face := (controls ->> 'face_amount')::numeric;
    source_discount := (controls ->> 'discount_amount')::numeric;
    source_fee := (controls ->> 'fee_amount')::numeric;
    source_net := (controls ->> 'net_amount')::numeric;
    source_orphans := (controls ->> 'orphan_segment_count')::integer;

    SELECT
        count(*),
        coalesce(sum(face_amount_brl), 0.00),
        coalesce(sum(discount_brl), 0.00),
        coalesce(sum(fee_brl), 0.00),
        coalesce(sum(net_amount_brl), 0.00)
      INTO
        staged_count,
        staged_face,
        staged_discount,
        staged_fee,
        staged_net
      FROM staging.payment_slip_settlement
     WHERE batch_id = p_batch_id;

    SELECT
        count(*),
        coalesce(sum(face_amount_brl), 0.00),
        coalesce(sum(discount_brl), 0.00),
        coalesce(sum(fee_brl), 0.00),
        coalesce(sum(net_amount_brl), 0.00)
      INTO
        applied_count,
        applied_face,
        applied_discount,
        applied_fee,
        applied_net
      FROM legacy.payment_slip_settlement
     WHERE batch_id = p_batch_id;

    SELECT count(*)
      INTO rejected
      FROM control.rejects
     WHERE batch_id = p_batch_id;

    INSERT INTO reporting.payment_slip_settlement_reconciliation (
        batch_id,
        currency,
        source_count,
        staged_count,
        applied_count,
        source_face_amount,
        staged_face_amount,
        applied_face_amount,
        source_discount_amount,
        staged_discount_amount,
        applied_discount_amount,
        source_fee_amount,
        staged_fee_amount,
        applied_fee_amount,
        source_net_amount,
        staged_net_amount,
        applied_net_amount,
        source_orphan_segment_count,
        staged_orphan_segment_count,
        applied_orphan_segment_count,
        count_delta,
        face_amount_delta,
        discount_amount_delta,
        fee_amount_delta,
        net_amount_delta,
        orphan_segment_count_delta,
        reject_count,
        status
    )
    VALUES (
        p_batch_id,
        'BRL',
        source_count,
        staged_count,
        applied_count,
        source_face,
        staged_face,
        applied_face,
        source_discount,
        staged_discount,
        applied_discount,
        source_fee,
        staged_fee,
        applied_fee,
        source_net,
        staged_net,
        applied_net,
        source_orphans,
        0,
        0,
        applied_count - source_count,
        applied_face - source_face,
        applied_discount - source_discount,
        applied_fee - source_fee,
        applied_net - source_net,
        0 - source_orphans,
        rejected,
        CASE
            WHEN source_count = staged_count
             AND source_count = applied_count
             AND source_face = staged_face
             AND source_face = applied_face
             AND source_discount = staged_discount
             AND source_discount = applied_discount
             AND source_fee = staged_fee
             AND source_fee = applied_fee
             AND source_net = staged_net
             AND source_net = applied_net
             AND source_orphans = 0
             AND rejected = 0
            THEN 'MATCHED'
            ELSE 'MISMATCHED'
        END
    )
    ON CONFLICT (batch_id, currency) DO UPDATE
       SET source_count = excluded.source_count,
           staged_count = excluded.staged_count,
           applied_count = excluded.applied_count,
           source_face_amount = excluded.source_face_amount,
           staged_face_amount = excluded.staged_face_amount,
           applied_face_amount = excluded.applied_face_amount,
           source_discount_amount = excluded.source_discount_amount,
           staged_discount_amount = excluded.staged_discount_amount,
           applied_discount_amount = excluded.applied_discount_amount,
           source_fee_amount = excluded.source_fee_amount,
           staged_fee_amount = excluded.staged_fee_amount,
           applied_fee_amount = excluded.applied_fee_amount,
           source_net_amount = excluded.source_net_amount,
           staged_net_amount = excluded.staged_net_amount,
           applied_net_amount = excluded.applied_net_amount,
           source_orphan_segment_count =
               excluded.source_orphan_segment_count,
           staged_orphan_segment_count =
               excluded.staged_orphan_segment_count,
           applied_orphan_segment_count =
               excluded.applied_orphan_segment_count,
           count_delta = excluded.count_delta,
           face_amount_delta = excluded.face_amount_delta,
           discount_amount_delta = excluded.discount_amount_delta,
           fee_amount_delta = excluded.fee_amount_delta,
           net_amount_delta = excluded.net_amount_delta,
           orphan_segment_count_delta =
               excluded.orphan_segment_count_delta,
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
        'reporting.refresh_payment_slip_settlement_reconciliation',
        'succeeded'
    )
    ON CONFLICT (batch_id, procedure_name) DO NOTHING;
END;
$$;

COMMENT ON TABLE staging.payment_slip_settlement IS
'Privacy-safe Type 03 logical settlements loaded from paired source segments.';

COMMENT ON FUNCTION
legacy.apply_payment_slip_settlement_batch(text) IS
'Idempotently applies immutable Type 03 settlement rows and rejects drift.';

COMMENT ON FUNCTION
reporting.refresh_payment_slip_settlement_reconciliation(text) IS
'Recomputes zero-tolerance Type 03 controls across all legacy boundaries.';

ALTER TABLE staging.payment_slip_settlement
    OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.payment_slip_settlement
    OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.payment_slip_settlement_reconciliation
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_payment_slip_settlement_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION
reporting.refresh_payment_slip_settlement_reconciliation(text)
    OWNER TO northwind_legacy_owner;

REVOKE ALL ON staging.payment_slip_settlement FROM PUBLIC;
REVOKE ALL ON legacy.payment_slip_settlement FROM PUBLIC;
REVOKE ALL ON reporting.payment_slip_settlement_reconciliation FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
legacy.apply_payment_slip_settlement_batch(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION
reporting.refresh_payment_slip_settlement_reconciliation(text)
    FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON staging.payment_slip_settlement TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT SELECT ON legacy.payment_slip_settlement, '
        'reporting.payment_slip_settlement_reconciliation TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'legacy.apply_payment_slip_settlement_batch(text) TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION '
        'reporting.refresh_payment_slip_settlement_reconciliation(text) '
        'TO %I',
        app_user
    );
END;
$$;
