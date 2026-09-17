\set ON_ERROR_STOP on

-- Expand the Type 01 control plane without changing its existing API.
ALTER TABLE control.batches
    DROP CONSTRAINT IF EXISTS batches_file_type_check;

ALTER TABLE control.batches
    ADD CONSTRAINT batches_file_type_check CHECK (
        file_type IN ('01', '02', '03', '04', '05')
    );

ALTER TABLE control.batches
    ADD COLUMN IF NOT EXISTS source_controls jsonb;

UPDATE control.batches
   SET source_controls = jsonb_build_object(
           'currency', 'BRL',
           'detail_count', source_count,
           'net_amount', to_char(source_net_amount, 'FM9999999999999990.00')
       )
 WHERE source_controls IS NULL
   AND file_type = '01';

ALTER TABLE control.batches
    ALTER COLUMN source_controls SET NOT NULL;

ALTER TABLE control.batches
    DROP CONSTRAINT IF EXISTS batches_source_controls_object_check;

ALTER TABLE control.batches
    ADD CONSTRAINT batches_source_controls_object_check CHECK (
        jsonb_typeof(source_controls) = 'object'
    );

ALTER TABLE control.loads
    ADD COLUMN IF NOT EXISTS stage_controls jsonb;

UPDATE control.loads AS load
   SET stage_controls = jsonb_build_object(
           'currency', 'BRL',
           'row_count', load.staged_count,
           'net_amount', to_char(
               load.staged_net_amount,
               'FM9999999999999990.00'
           )
       )
 WHERE load.stage_controls IS NULL;

ALTER TABLE control.loads
    ALTER COLUMN stage_controls SET NOT NULL;

ALTER TABLE control.loads
    DROP CONSTRAINT IF EXISTS loads_stage_controls_object_check;

ALTER TABLE control.loads
    ADD CONSTRAINT loads_stage_controls_object_check CHECK (
        jsonb_typeof(stage_controls) = 'object'
    );

ALTER TABLE control.rejects
    ADD COLUMN IF NOT EXISTS computed_controls jsonb,
    ADD COLUMN IF NOT EXISTS declared_controls jsonb;

CREATE OR REPLACE FUNCTION control.populate_legacy_control_maps()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.source_controls IS NULL AND NEW.file_type = '01' THEN
        NEW.source_controls := jsonb_build_object(
            'currency', 'BRL',
            'detail_count', NEW.source_count,
            'net_amount', to_char(
                NEW.source_net_amount,
                'FM9999999999999990.00'
            )
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS batches_populate_legacy_control_maps
    ON control.batches;

CREATE TRIGGER batches_populate_legacy_control_maps
BEFORE INSERT ON control.batches
FOR EACH ROW
EXECUTE FUNCTION control.populate_legacy_control_maps();

CREATE OR REPLACE FUNCTION control.populate_legacy_stage_maps()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.stage_controls IS NULL THEN
        NEW.stage_controls := jsonb_build_object(
            'currency', 'BRL',
            'row_count', NEW.staged_count,
            'net_amount', to_char(
                NEW.staged_net_amount,
                'FM9999999999999990.00'
            )
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS loads_populate_legacy_stage_maps
    ON control.loads;

CREATE TRIGGER loads_populate_legacy_stage_maps
BEFORE INSERT ON control.loads
FOR EACH ROW
EXECUTE FUNCTION control.populate_legacy_stage_maps();

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
    controls_net numeric;
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
        controls_net := (p_source_controls ->> 'net_amount')::numeric;
    EXCEPTION
        WHEN invalid_text_representation OR numeric_value_out_of_range THEN
            RAISE EXCEPTION 'Source control map is not canonical'
                USING ERRCODE = '22023';
    END;
    IF controls_count IS DISTINCT FROM p_source_count
       OR controls_net IS DISTINCT FROM p_source_net_amount THEN
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

CREATE OR REPLACE FUNCTION control.register_load_v2(
    p_batch_id text,
    p_stage_controls jsonb,
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
    IF jsonb_typeof(p_stage_controls) <> 'object' THEN
        RAISE EXCEPTION 'Stage control map must be an object'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO control.loads (
        batch_id,
        staged_count,
        staged_net_amount,
        stage_controls,
        status
    )
    VALUES (
        p_batch_id,
        p_staged_count,
        p_staged_net_amount,
        p_stage_controls,
        'loaded'
    )
    ON CONFLICT (batch_id) DO NOTHING;

    SELECT *
      INTO STRICT observed
      FROM control.loads
     WHERE batch_id = p_batch_id;
    IF observed.staged_count <> p_staged_count
       OR observed.staged_net_amount <> p_staged_net_amount
       OR observed.stage_controls <> p_stage_controls
       OR observed.status <> 'loaded' THEN
        RAISE EXCEPTION 'Load controls changed on replay'
            USING ERRCODE = 'P0001';
    END IF;
END;
$$;

COMMENT ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) IS
'Registers immutable source identity and exact type-specific controls. '
'Replays succeed only when identity, controls, and legal state agree.';

COMMENT ON FUNCTION control.register_load_v2(
    text, jsonb, integer, numeric
) IS
'Registers immutable privacy-safe staging controls for one batch.';

ALTER TABLE control.batches OWNER TO northwind_legacy_owner;
ALTER TABLE control.loads OWNER TO northwind_legacy_owner;
ALTER TABLE control.rejects OWNER TO northwind_legacy_owner;

ALTER FUNCTION control.populate_legacy_control_maps()
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.populate_legacy_stage_maps()
    OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) OWNER TO northwind_legacy_owner;
ALTER FUNCTION control.register_load_v2(
    text, jsonb, integer, numeric
) OWNER TO northwind_legacy_owner;

REVOKE EXECUTE ON FUNCTION control.populate_legacy_control_maps()
    FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION control.populate_legacy_stage_maps()
    FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION control.register_batch_v2(
    text, text, text, text, text, jsonb, integer, numeric, text, text
) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION control.register_load_v2(
    text, jsonb, integer, numeric
) FROM PUBLIC;

DO $$
DECLARE
    app_user text := current_setting('northwind.app_user');
BEGIN
    EXECUTE format(
        'GRANT SELECT ON control.batches, control.loads TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION control.register_batch_v2('
        'text, text, text, text, text, jsonb, integer, numeric, text, text'
        ') TO %I',
        app_user
    );
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION control.register_load_v2('
        'text, jsonb, integer, numeric'
        ') TO %I',
        app_user
    );
END;
$$;
