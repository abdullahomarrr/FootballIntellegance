# Fantasy Premier League public feed (current stats tier)

Added 2026-10-01 with the product owner's approval for portfolio use.

## What it is

The public, read-only JSON endpoints behind the Fantasy Premier League site
(`bootstrap-static` and `element-summary/{id}`). They are **unofficial and undocumented, with no
stated licence**. Fans use them widely and they need no login, but reuse has not been granted.

## How it is used

- Fetched on demand, cached for one hour in memory and on disk (`data/external/fpl`, git-ignored),
  requests spaced at least a second apart, with an identifying User-Agent. Nothing is republished
  in bulk and no raw payload is committed.
- Supplies for every current Premier League player: season totals, expected goals and assists,
  tackles, recoveries, clearances/blocks/interceptions, defensive contributions, availability news
  and chance of playing, birth date, and past-season totals (and per-gameweek rows).
- Shown as a clearly labelled **stats tier**: no event locations, so no heatmaps, pass maps, xT or
  archetypes. Rankings are per-90 percentiles against current Premier League players of the same
  position with a minutes floor (`max(90, 36% of minutes available)`), and are provisional early in
  a season because cohorts are small.
- The FPL price is a fantasy-game price, never a market value or a transfer fee.

## Linking to our players

Exact IDs first: the FPL `code` equals Reep's `key_opta_numeric`, which resolves to a Wyscout or
Transfermarkt ID already in our warehouse. Otherwise a unique birth date plus name match. Links are
stored in `bridge_player_fpl`. About 146 of 667 current players have an older event profile; the
rest are stats-tier only.

## Reep crosswalk

`withqwerty/reep` (CC0, derived from Wikidata, frozen June 2026) is loaded into `reep_crosswalk`
(47,847 players with a Wyscout, Transfermarkt or Opta ID) by `load-reep-crosswalk`. It carries IDs
only. It was used to audit the earlier name-based Transfermarkt links (99.5% agreement) and now
overrides them where an exact ID exists (2,491 players).

## Limits

Premier League only; current season and past Premier League seasons only; the feed can change or
disappear without notice, in which case the stats tier degrades to a clear "feed unavailable" state.
