CREATE TABLE IF NOT EXISTS player_alias (
    player_alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    alias text NOT NULL,
    normalized_alias text NOT NULL,
    language text,
    source text NOT NULL,
    verified boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (player_id, normalized_alias, source)
);

CREATE UNIQUE INDEX IF NOT EXISTS bridge_player_provider_current_uidx
    ON bridge_player_provider (provider, provider_player_id)
    WHERE valid_to IS NULL;

