-- Reep (CC0, Wikidata-derived) ID crosswalk and the FPL feed link table.
CREATE TABLE IF NOT EXISTS reep_crosswalk (
    reep_id text PRIMARY KEY,
    opta_numeric text,
    tm_player_id bigint,
    wyscout_id text,
    name text,
    date_of_birth date
);
CREATE INDEX IF NOT EXISTS reep_crosswalk_opta_idx ON reep_crosswalk (opta_numeric);
CREATE INDEX IF NOT EXISTS reep_crosswalk_wyscout_idx ON reep_crosswalk (wyscout_id);
CREATE INDEX IF NOT EXISTS reep_crosswalk_tm_idx ON reep_crosswalk (tm_player_id);

CREATE TABLE IF NOT EXISTS bridge_player_fpl (
    fpl_code bigint PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    link_basis text NOT NULL,
    built_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bridge_player_fpl_player_idx ON bridge_player_fpl (player_id);
