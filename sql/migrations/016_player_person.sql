-- Presentation-level grouping of provider identities that are the same person.
-- Facts stay keyed by provider identity (no double counting); profiles read through this map.
CREATE TABLE IF NOT EXISTS player_person (
    player_id bigint PRIMARY KEY REFERENCES dim_player(player_id),
    person_id bigint NOT NULL,
    link_basis text NOT NULL,
    built_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS player_person_person_idx ON player_person (person_id);
