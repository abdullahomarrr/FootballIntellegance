CREATE TABLE IF NOT EXISTS bridge_team_provider (
    team_id bigint NOT NULL REFERENCES dim_team(team_id),
    provider text NOT NULL,
    provider_team_id text NOT NULL,
    provider_name text NOT NULL,
    confidence numeric(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    match_method text NOT NULL,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz,
    PRIMARY KEY (provider, provider_team_id, valid_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS bridge_team_provider_current_uidx
    ON bridge_team_provider (provider, provider_team_id) WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS bridge_competition_provider (
    competition_id bigint NOT NULL REFERENCES dim_competition(competition_id),
    provider text NOT NULL,
    provider_competition_id text NOT NULL,
    provider_name text NOT NULL,
    PRIMARY KEY (provider, provider_competition_id)
);

CREATE TABLE IF NOT EXISTS bridge_season_provider (
    season_id bigint NOT NULL REFERENCES dim_season(season_id),
    provider text NOT NULL,
    provider_season_id text NOT NULL,
    PRIMARY KEY (provider, provider_season_id)
);

CREATE TABLE IF NOT EXISTS bridge_match_provider (
    match_id bigint NOT NULL REFERENCES dim_match(match_id),
    provider text NOT NULL,
    provider_match_id text NOT NULL,
    source_label text,
    PRIMARY KEY (provider, provider_match_id)
);

