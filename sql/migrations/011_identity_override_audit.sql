CREATE TABLE IF NOT EXISTS identity_override_audit (
    override_id text PRIMARY KEY,
    override_version integer NOT NULL CHECK (override_version > 0),
    provider text NOT NULL,
    provider_player_id text NOT NULL,
    previous_player_id bigint REFERENCES dim_player(player_id),
    target_player_id bigint NOT NULL REFERENCES dim_player(player_id),
    reason text NOT NULL,
    approved_by text NOT NULL,
    approved_at timestamptz NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

