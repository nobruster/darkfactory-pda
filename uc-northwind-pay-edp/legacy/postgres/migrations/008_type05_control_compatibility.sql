\set ON_ERROR_STOP on

-- The original control plane exposed one compatibility "net" column.
-- Type 05 has no net concept, so its assessed fee is the explicit scalar
-- projection while source_controls remains the complete authoritative map.
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
    IF p_file_type NOT IN ('01', '02', '03', '04', '05')
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
            (p_source_controls ->> 'assessed_fee')::numeric
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

COMMENT ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) IS
'Registers immutable source identity and complete type controls. The legacy '
'compatibility amount is net for Types 01-04 and assessed fee for Type 05.';

ALTER FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) OWNER TO northwind_legacy_owner;

REVOKE EXECUTE ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION control.register_batch_v2('
        'text, text, text, text, text, jsonb, integer, numeric, text, text'
        ') TO %I',
        app_user
    );
END;
$$;
