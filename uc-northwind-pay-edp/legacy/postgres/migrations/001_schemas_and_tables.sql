\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS control;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS legacy;
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE IF NOT EXISTS control.batches (
    batch_id text PRIMARY KEY CHECK (batch_id ~ '^B[0-9]{15}$'),
    file_type text NOT NULL CHECK (file_type = '01'),
    source_filename text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    source_manifest_sha256 text NOT NULL
        CHECK (source_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    source_count integer NOT NULL CHECK (source_count > 0),
    source_net_amount numeric(18, 2) NOT NULL,
    status text NOT NULL CHECK (
        status IN (
            'claimed',
            'sanitized',
            'loaded',
            'database_committed_pending_archive',
            'succeeded',
            'quarantined',
            'failed',
            'oracle_mismatch'
        )
    ),
    failure_code text,
    CHECK (
        (status = 'quarantined' AND failure_code IS NOT NULL)
        OR status <> 'quarantined'
    )
);

ALTER TABLE control.batches
    DROP CONSTRAINT IF EXISTS batches_status_check;

ALTER TABLE control.batches
    ADD CONSTRAINT batches_status_check CHECK (
        status IN (
            'claimed',
            'sanitized',
            'loaded',
            'database_committed_pending_archive',
            'succeeded',
            'quarantined',
            'failed',
            'oracle_mismatch'
        )
    );

CREATE TABLE IF NOT EXISTS control.files (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    stage text NOT NULL CHECK (stage IN ('raw', 'sanitized_csv')),
    filename text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    PRIMARY KEY (batch_id, stage)
);

CREATE TABLE IF NOT EXISTS control.loads (
    batch_id text PRIMARY KEY REFERENCES control.batches(batch_id),
    staged_count integer NOT NULL CHECK (staged_count >= 0),
    staged_net_amount numeric(18, 2) NOT NULL,
    status text NOT NULL CHECK (status IN ('loaded', 'rolled_back'))
);

CREATE TABLE IF NOT EXISTS control.rejects (
    batch_id text NOT NULL,
    stage text NOT NULL,
    code text NOT NULL,
    record_number integer,
    transaction_id text,
    computed_count integer CHECK (
        computed_count IS NULL OR computed_count >= 0
    ),
    computed_net_amount numeric(18, 2),
    declared_count integer CHECK (
        declared_count IS NULL OR declared_count >= 0
    ),
    declared_net_amount numeric(18, 2),
    PRIMARY KEY (batch_id, stage, code)
);

ALTER TABLE control.rejects
    ADD COLUMN IF NOT EXISTS computed_count integer,
    ADD COLUMN IF NOT EXISTS computed_net_amount numeric(18, 2),
    ADD COLUMN IF NOT EXISTS declared_count integer,
    ADD COLUMN IF NOT EXISTS declared_net_amount numeric(18, 2);

ALTER TABLE control.rejects
    DROP CONSTRAINT IF EXISTS rejects_computed_count_check,
    DROP CONSTRAINT IF EXISTS rejects_declared_count_check;

ALTER TABLE control.rejects
    ADD CONSTRAINT rejects_computed_count_check CHECK (
        computed_count IS NULL OR computed_count >= 0
    ),
    ADD CONSTRAINT rejects_declared_count_check CHECK (
        declared_count IS NULL OR declared_count >= 0
    );

CREATE TABLE IF NOT EXISTS control.procedure_runs (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    sequence_number integer NOT NULL CHECK (sequence_number > 0),
    procedure_name text NOT NULL,
    status text NOT NULL CHECK (status IN ('succeeded', 'failed')),
    PRIMARY KEY (batch_id, procedure_name)
);

CREATE TABLE IF NOT EXISTS staging.card_settlement (
    batch_id text NOT NULL REFERENCES control.batches(batch_id),
    source_file text NOT NULL,
    source_record_number integer NOT NULL CHECK (source_record_number > 1),
    transaction_id text NOT NULL CHECK (transaction_id ~ '^[A-Z0-9]{16}$'),
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Z0-9]{16}$'),
    card_token text NOT NULL CHECK (card_token ~ '^tok_[0-9a-f]{24}$'),
    card_last4 text NOT NULL CHECK (card_last4 ~ '^[0-9]{4}$'),
    cpf_masked text NOT NULL CHECK (cpf_masked ~ '^\*{7}[0-9]{4}$'),
    transaction_ts timestamptz NOT NULL,
    amount_brl numeric(18, 2) NOT NULL,
    movement_code text NOT NULL CHECK (movement_code IN ('P', 'R')),
    authorization_code text NOT NULL CHECK (
        authorization_code ~ '^[A-Z0-9]{6}$'
    ),
    nsu text NOT NULL CHECK (nsu ~ '^[0-9]{12}$'),
    terminal_id text NOT NULL CHECK (terminal_id ~ '^[A-Z0-9]{16}$'),
    PRIMARY KEY (batch_id, source_record_number),
    UNIQUE (batch_id, transaction_id),
    CHECK (
        (movement_code = 'P' AND amount_brl > 0)
        OR (movement_code = 'R' AND amount_brl < 0)
    )
);

CREATE TABLE IF NOT EXISTS legacy.card_settlement (
    batch_id text NOT NULL,
    source_file text NOT NULL,
    source_record_number integer NOT NULL,
    transaction_id text NOT NULL,
    merchant_id text NOT NULL,
    card_token text NOT NULL CHECK (card_token ~ '^tok_[0-9a-f]{24}$'),
    card_last4 text NOT NULL CHECK (card_last4 ~ '^[0-9]{4}$'),
    cpf_masked text NOT NULL CHECK (cpf_masked ~ '^\*{7}[0-9]{4}$'),
    transaction_ts timestamptz NOT NULL,
    amount_brl numeric(18, 2) NOT NULL,
    movement_code text NOT NULL CHECK (movement_code IN ('P', 'R')),
    authorization_code text NOT NULL,
    nsu text NOT NULL,
    terminal_id text NOT NULL,
    PRIMARY KEY (batch_id, source_record_number),
    UNIQUE (batch_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS reporting.card_settlement_reconciliation (
    batch_id text NOT NULL,
    currency text NOT NULL CHECK (currency = 'BRL'),
    source_count integer NOT NULL,
    staged_count integer NOT NULL,
    applied_count integer NOT NULL,
    source_net_amount numeric(18, 2) NOT NULL,
    staged_net_amount numeric(18, 2) NOT NULL,
    applied_net_amount numeric(18, 2) NOT NULL,
    count_delta integer NOT NULL,
    amount_delta numeric(18, 2) NOT NULL,
    reject_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('MATCHED', 'MISMATCHED')),
    PRIMARY KEY (batch_id, currency)
);
