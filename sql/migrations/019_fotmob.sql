-- Current first-team squads for the top-5 leagues (read from FotMob's public team pages) and the
-- link from a squad player to our own player record. Personal-use data, see
-- docs/data_sources/fotmob-pages.md.
CREATE TABLE IF NOT EXISTS fotmob_team (
    team_id integer PRIMARY KEY,
    name text NOT NULL,
    league_id integer NOT NULL,
    league_name text NOT NULL,
    season text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fotmob_squad_member (
    player_id integer PRIMARY KEY,
    team_id integer NOT NULL REFERENCES fotmob_team(team_id) ON DELETE CASCADE,
    name text NOT NULL,
    position_group text NOT NULL,
    role text,
    position_codes text,
    shirt_number integer,
    nationality text,
    nationality_code text,
    birth_date date,
    height_cm integer,
    age integer,
    market_value_eur bigint,
    injured boolean NOT NULL DEFAULT false,
    injury_return text,
    rating numeric,
    goals integer,
    assists integer,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fotmob_squad_member_team_idx ON fotmob_squad_member (team_id);

CREATE TABLE IF NOT EXISTS bridge_player_fotmob (
    fotmob_id integer PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    link_basis text NOT NULL,
    built_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bridge_player_fotmob_player_idx ON bridge_player_fotmob (player_id);
