ALTER TABLE fact_event
    ADD COLUMN IF NOT EXISTS provider_match_id text,
    ADD COLUMN IF NOT EXISTS provider_player_id text,
    ADD COLUMN IF NOT EXISTS provider_team_id text;

CREATE INDEX IF NOT EXISTS fact_event_provider_match_idx
    ON fact_event (provider, provider_match_id);

CREATE INDEX IF NOT EXISTS fact_event_provider_player_idx
    ON fact_event (provider, provider_player_id)
    WHERE provider_player_id IS NOT NULL;

