-- Parsed FotMob player pages (personal use, see docs/data_sources/fotmob-pages.md) kept in the
-- database so a host without the local disk cache can still build the alternatives pool.
-- Refresh with `football-intelligence sync-fotmob-profiles` after warming the cache.
CREATE TABLE IF NOT EXISTS fotmob_player_profile (
    player_id bigint PRIMARY KEY,
    payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL
);
