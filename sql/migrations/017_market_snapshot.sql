-- Third-party historical market snapshot (dcaribou/transfermarkt-datasets, frozen June 2026).
CREATE TABLE IF NOT EXISTS bridge_player_transfermarkt (
    player_id bigint PRIMARY KEY REFERENCES dim_player(player_id),
    tm_player_id bigint NOT NULL,
    match_basis text NOT NULL,
    tm_name text,
    built_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bridge_player_tm_idx ON bridge_player_transfermarkt (tm_player_id);

ALTER TABLE fact_transfer
    ADD COLUMN IF NOT EXISTS from_club_name text,
    ADD COLUMN IF NOT EXISTS to_club_name text,
    ADD COLUMN IF NOT EXISTS transfer_season text;

CREATE TABLE IF NOT EXISTS player_contract_observation (
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    provider text NOT NULL,
    contract_expires date NOT NULL,
    club_name text,
    observed_as_of date NOT NULL,
    provenance_raw_object_uri text NOT NULL,
    PRIMARY KEY (player_id, provider, contract_expires)
);
