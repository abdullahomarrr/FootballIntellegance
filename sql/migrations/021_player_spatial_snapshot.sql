-- Precomputed spatial payloads (heatmaps, pass lines, threat zones, shots) per
-- player-team-competition-season. Lets a hosted deployment serve the visuals without
-- shipping the multi-gigabyte fact_event table. Rebuild with
-- `football-intelligence build-spatial-snapshot` after loading new events.
CREATE TABLE IF NOT EXISTS player_spatial_snapshot (
    player_id bigint NOT NULL,
    team_id bigint,
    competition_id bigint NOT NULL,
    season_id bigint NOT NULL,
    payload jsonb NOT NULL,
    built_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS player_spatial_snapshot_key
    ON player_spatial_snapshot (player_id, team_id, competition_id, season_id) NULLS NOT DISTINCT;
