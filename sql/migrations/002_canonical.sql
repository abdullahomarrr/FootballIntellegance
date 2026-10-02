CREATE TABLE IF NOT EXISTS dim_player (
    player_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_name text NOT NULL,
    normalized_name text NOT NULL,
    birth_date date,
    nationality_codes text[],
    preferred_foot text,
    height_cm smallint CHECK (height_cm BETWEEN 120 AND 230),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS dim_player_identity_idx
    ON dim_player (normalized_name, birth_date);

CREATE TABLE IF NOT EXISTS dim_team (
    team_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_name text NOT NULL,
    country_code text,
    team_type text NOT NULL DEFAULT 'CLUB',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_competition (
    competition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_name text NOT NULL,
    country_code text,
    competition_type text
);

DO $$
BEGIN
    CREATE TYPE season_status AS ENUM ('IN_PROGRESS', 'FINAL', 'PARTIAL');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS dim_season (
    season_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    label text NOT NULL UNIQUE,
    start_date date,
    end_date date,
    status season_status NOT NULL,
    data_as_of timestamptz
);

CREATE TABLE IF NOT EXISTS bridge_player_provider (
    bridge_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    provider text NOT NULL,
    provider_player_id text NOT NULL,
    provider_name text NOT NULL,
    confidence numeric(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    match_method text NOT NULL,
    verified boolean NOT NULL DEFAULT false,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz,
    UNIQUE (provider, provider_player_id, valid_from)
);

CREATE TABLE IF NOT EXISTS entity_resolution_candidate (
    candidate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type text NOT NULL,
    provider text NOT NULL,
    provider_entity_id text NOT NULL,
    canonical_candidate_id bigint,
    score numeric(5,4) NOT NULL CHECK (score BETWEEN 0 AND 1),
    signals jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    reviewer text,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_match (
    match_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    competition_id bigint REFERENCES dim_competition(competition_id),
    season_id bigint REFERENCES dim_season(season_id),
    home_team_id bigint REFERENCES dim_team(team_id),
    away_team_id bigint REFERENCES dim_team(team_id),
    kickoff_at timestamptz,
    status text,
    home_score smallint,
    away_score smallint,
    data_as_of timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_event (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL,
    provider_event_id text NOT NULL,
    match_id bigint REFERENCES dim_match(match_id),
    player_id bigint REFERENCES dim_player(player_id),
    team_id bigint REFERENCES dim_team(team_id),
    period text,
    minute smallint,
    second numeric(8,3),
    event_type text NOT NULL,
    event_subtype text,
    outcome text,
    raw_x numeric,
    raw_y numeric,
    raw_end_x numeric,
    raw_end_y numeric,
    coordinate_system text,
    normalized_x_m numeric CHECK (normalized_x_m BETWEEN 0 AND 105),
    normalized_y_m numeric CHECK (normalized_y_m BETWEEN 0 AND 68),
    normalized_end_x_m numeric CHECK (normalized_end_x_m BETWEEN 0 AND 105),
    normalized_end_y_m numeric CHECK (normalized_end_y_m BETWEEN 0 AND 68),
    attacking_direction_normalized boolean NOT NULL DEFAULT false,
    shot_xg numeric CHECK (shot_xg BETWEEN 0 AND 1),
    qualifiers jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_schema_version text,
    data_as_of timestamptz NOT NULL,
    UNIQUE (provider, provider_event_id)
);

