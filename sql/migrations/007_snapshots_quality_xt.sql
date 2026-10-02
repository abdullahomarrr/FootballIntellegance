CREATE TABLE IF NOT EXISTS data_quarantine (
    quarantine_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id text REFERENCES pipeline_run(pipeline_run_id),
    provider text NOT NULL,
    entity_type text NOT NULL,
    provider_entity_id text,
    reason_code text NOT NULL,
    raw_object_uri text,
    payload jsonb NOT NULL,
    quarantined_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    resolution_note text
);

CREATE INDEX IF NOT EXISTS data_quarantine_open_idx
    ON data_quarantine (provider, reason_code, quarantined_at DESC)
    WHERE resolved_at IS NULL;

CREATE TABLE IF NOT EXISTS mart_player_season_snapshot (
    snapshot_date date NOT NULL,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    competition_id bigint NOT NULL REFERENCES dim_competition(competition_id),
    season_id bigint NOT NULL REFERENCES dim_season(season_id),
    team_id bigint REFERENCES dim_team(team_id),
    minutes integer NOT NULL DEFAULT 0,
    appearances integer NOT NULL DEFAULT 0,
    metrics jsonb NOT NULL,
    feature_set_version text NOT NULL,
    data_as_of timestamptz NOT NULL,
    PRIMARY KEY (snapshot_date, player_id, competition_id, season_id, feature_set_version)
);

CREATE TABLE IF NOT EXISTS fact_event_derived_metric (
    event_id bigint NOT NULL REFERENCES fact_event(event_id) ON DELETE CASCADE,
    metric_name text NOT NULL,
    metric_value numeric NOT NULL,
    model_version text NOT NULL,
    data_as_of timestamptz NOT NULL,
    PRIMARY KEY (event_id, metric_name, model_version)
);
