CREATE TABLE IF NOT EXISTS source_observation (
    observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL,
    entity_type text NOT NULL,
    provider_entity_id text NOT NULL,
    observed_at timestamptz NOT NULL,
    source_url text NOT NULL,
    source_license text,
    raw_object_uri text NOT NULL,
    content_hash text NOT NULL,
    payload jsonb NOT NULL,
    UNIQUE (provider, entity_type, provider_entity_id, content_hash)
);

CREATE INDEX IF NOT EXISTS source_observation_entity_idx
    ON source_observation (entity_type, provider_entity_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS source_conflict (
    conflict_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type text NOT NULL,
    canonical_entity_id bigint,
    field_name text NOT NULL,
    left_provider text NOT NULL,
    left_value jsonb,
    right_provider text NOT NULL,
    right_value jsonb,
    detected_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'RESOLVED', 'EXPECTED_VARIANCE')),
    resolution_note text,
    UNIQUE (entity_type, canonical_entity_id, field_name, left_provider, right_provider)
);
