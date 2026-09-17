#!/bin/sh
set -eu

: "${POSTGRES_APP_USER:?POSTGRES_APP_USER is required}"

psql \
    --set=ON_ERROR_STOP=1 \
    --set=app_user="$POSTGRES_APP_USER" \
    --set=database="$POSTGRES_DB" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" <<'SQL'
ALTER SCHEMA control OWNER TO northwind_legacy_owner;
ALTER SCHEMA staging OWNER TO northwind_legacy_owner;
ALTER SCHEMA legacy OWNER TO northwind_legacy_owner;
ALTER SCHEMA reporting OWNER TO northwind_legacy_owner;

ALTER TABLE control.batches OWNER TO northwind_legacy_owner;
ALTER TABLE control.files OWNER TO northwind_legacy_owner;
ALTER TABLE control.loads OWNER TO northwind_legacy_owner;
ALTER TABLE control.rejects OWNER TO northwind_legacy_owner;
ALTER TABLE control.procedure_runs OWNER TO northwind_legacy_owner;
ALTER TABLE staging.card_settlement OWNER TO northwind_legacy_owner;
ALTER TABLE legacy.card_settlement OWNER TO northwind_legacy_owner;
ALTER TABLE reporting.card_settlement_reconciliation
    OWNER TO northwind_legacy_owner;

ALTER FUNCTION control.register_batch(
    text, text, text, text, integer, numeric, text, text
) OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_file(text, text, text, text, bigint)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_load(text, integer, numeric)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_reject(
    text, text, text, integer, numeric, integer, numeric
) OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.mark_batch_committed(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.mark_batch_succeeded(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION legacy.apply_card_settlement_batch(text)
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION reporting.refresh_card_settlement_reconciliation(text)
    OWNER TO northwind_legacy_owner;

GRANT CONNECT ON DATABASE :"database" TO :"app_user";

GRANT USAGE ON SCHEMA control, staging, legacy, reporting
TO :"app_user";

REVOKE ALL ON ALL TABLES IN SCHEMA
    control, staging, legacy, reporting
FROM :"app_user";

GRANT SELECT ON
    control.batches,
    control.files,
    control.loads,
    control.rejects,
    control.procedure_runs,
    staging.card_settlement,
    legacy.card_settlement,
    reporting.card_settlement_reconciliation
TO :"app_user";

GRANT INSERT ON staging.card_settlement TO :"app_user";

REVOKE EXECUTE ON FUNCTION
    control.register_batch(
        text, text, text, text, integer, numeric, text, text
    ),
    control.register_file(text, text, text, text, bigint),
    control.register_load(text, integer, numeric),
    control.register_reject(
        text, text, text, integer, numeric, integer, numeric
    ),
    control.mark_batch_committed(text),
    control.mark_batch_succeeded(text),
    legacy.apply_card_settlement_batch(text),
    reporting.refresh_card_settlement_reconciliation(text)
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
    control.register_batch(
        text, text, text, text, integer, numeric, text, text
    ),
    control.register_file(text, text, text, text, bigint),
    control.register_load(text, integer, numeric),
    control.register_reject(
        text, text, text, integer, numeric, integer, numeric
    ),
    control.mark_batch_committed(text),
    control.mark_batch_succeeded(text),
    legacy.apply_card_settlement_batch(text),
    reporting.refresh_card_settlement_reconciliation(text)
TO :"app_user";
SQL
