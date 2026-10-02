DO $$
BEGIN
    CREATE TYPE capability_status AS ENUM (
        'DIRECT', 'DERIVABLE', 'UNAVAILABLE', 'PAID', 'UNKNOWN'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS raw_object_manifest (
    raw_object_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL,
    endpoint text NOT NULL,
    request_parameters jsonb NOT NULL,
    ingested_at timestamptz NOT NULL,
    source_updated_at timestamptz,
    pipeline_run_id text NOT NULL,
    object_uri text NOT NULL UNIQUE,
    byte_size bigint NOT NULL CHECK (byte_size >= 0),
    checksum_sha256 text NOT NULL CHECK (checksum_sha256 ~ '^[a-f0-9]{64}$'),
    content_type text NOT NULL,
    source_schema_version text,
    terms_version text
);

CREATE TABLE IF NOT EXISTS provider_coverage_observation (
    coverage_observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL,
    plan text,
    provider_competition_id text NOT NULL,
    provider_season_id text NOT NULL,
    competition_name text NOT NULL,
    season_label text NOT NULL,
    capability text NOT NULL,
    status capability_status NOT NULL,
    checked_at timestamptz NOT NULL,
    provider_updated_at timestamptz,
    raw_object_uri text NOT NULL,
    checksum_sha256 text NOT NULL CHECK (checksum_sha256 ~ '^[a-f0-9]{64}$'),
    terms_version text,
    notes text,
    UNIQUE (provider, plan, provider_competition_id, provider_season_id, capability, checked_at)
);

CREATE INDEX IF NOT EXISTS provider_coverage_latest_idx
    ON provider_coverage_observation (provider, provider_competition_id, provider_season_id, capability, checked_at DESC);

