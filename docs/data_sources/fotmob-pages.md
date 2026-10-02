# FotMob public pages (personal use only)

## Status and terms

FotMob has no public API, and its terms do not permit scraping. This source was added at the
project owner's explicit request for a **local, personal-use** project. **Remove it before any
public deployment or portfolio hosting** (`fotmob.py`, `squad_routes.py`, `alternatives.py`, the
`/squads` page and migration 019).

Guard rails in the code:

- It reads only the server-rendered HTML a browser receives. It never calls FotMob's separate data
  API, which answers `null` without a signed header, and it does not try to forge that header.
- Requests identify the project honestly (`FootballIntelligencePortfolio/1.0 ... personal
  portfolio project`) and are spaced one second apart.
- Everything is cached on disk under `data/external/fotmob/` (git-ignored): league and squad
  pages for a day, player pages for a day. Normal use of the app touches the site rarely.
- Profile warming is opt-in and resumable, and stops after five consecutive failures instead of
  retrying a site that is refusing requests.
- Pages are shown as "FotMob" data and are never redistributed.

## What is read

| Page | What it yields |
|---|---|
| `/leagues/{id}/overview/...` | The clubs in the league's table (Premier League 47, La Liga 87, Serie A 55, Bundesliga 54, Ligue 1 53) |
| `/teams/{id}/squad/...` | The full first team: id, name, shirt number, nationality, role, position codes, **date of birth**, height, age, market value, injury status and return date, rating, goals, assists |
| `/players/{id}/...` | Per-90 values and FotMob percentile ranks for about 40 stats (shooting, passing, possession, defending, physical), peer-comparison traits for the role, heat map coordinates, an xG-tagged shot map, market value history, contract end, positions, foot and height |

## Loading

```bash
uv run python -m football_intelligence.cli load-fotmob-squads     # ~100 requests, all clubs
uv run python -m football_intelligence.cli warm-fotmob-profiles   # one page per player who has played
```

`load-fotmob-squads` covers every club in the five leagues for the current season (20 + 20 + 20 +
18 + 18) and links squad players to our own records. `warm-fotmob-profiles` fetches the player
page of everyone who has a match rating this season, most valuable first, and skips pages already
cached. A cold warm-up of about 1,900 players takes roughly an hour at one request per second.
Pages are also fetched on demand the first time a player is opened in the app.

## Linking to our own data

Squad players carry a date of birth, so they link to our player table on the **same birth date
and a matching name** (exact name variant, or every word of the squad name inside our longer legal
name), only when exactly one of our players fits. This is stricter than name-only matching.
Players it cannot link simply have no "older event profile" badge.

## Where the data shows up on the main profile

A player's main profile (`/players/{id}`) gets a **Current season** panel when that player is in a
current top-five-league squad: headline numbers, FotMob's role ranking, the heat map, an xG-tagged
shot map and grouped per-90 stats. It is aimed at players whose open event data is old or thin
(for example Lamine Yamal, whose event profile is a few tournament matches but who has 581 league
minutes this season). The panel reads `/players/{id}/current-season`, which fetches the linked
player's FotMob page (cached for a day) and renders nothing when there is no link.

### Link tiers

1. same birth date and an exact name fit, or every word of the squad name inside our longer legal
   name (`BIRTH_DATE_AND_NAME`, `BIRTH_DATE_AND_NAME_WORDS`);
2. for players we hold **no birth date** for (many tournament-only records, including Yamal): one
   exact name fit whose latest Transfermarkt contract club is the squad's club (`NAME_AND_CLUB`,
   `NAME_WORDS_AND_CLUB`).

Links went from 360 to 642. Every one of the 11 name-spelling differences among the new links was
checked by hand and was the right person.

## Lineup view

Opening a club shows an estimated starting XI on a pitch, with the rest of the squad listed below.
The XI is the goalkeeper plus the ten outfield players with the most minutes this season (match
rating, then market value, as tiebreaks), kept to a playable shape (3-5 at the back is allowed but
at most four defenders, at most three forwards) and ordered left to right from the position codes
FotMob lists. It shows who has played most, **not an official team sheet**, and the page says so.
Clicking a player opens a modal with the profile and alternatives; Escape or the close button
dismisses it. Across all 96 clubs the shapes are 4-3-3 (31), 4-4-2 (21), 3-5-2 (18), 4-5-1 (13)
and 3-4-3 (13).

## Alternatives finder

For the clicked player the app compares this season's per-90 numbers with every cached player in
the **same role family** (FotMob's own grouping: keepers, fullbacks, centre-backs, midfielders,
wingers, strikers) who has at least 180 minutes. Each stat is re-ranked across the whole pool, so
numbers are comparable across leagues rather than relying on FotMob's per-league percentiles.

- **Similarity** is 100 minus the mean gap between the two players' percentile profiles, over the
  stats both have (at least ten). Discipline, team-context stats and top speed are left out;
  fouls committed, dispossessed and dribbled past count lower-is-better. Rate stats that swing on
  a handful of attempts (long-ball, cross and dribble success rates, duel and aerial percentages)
  and penalty counts are dropped; pass accuracy and save percentage stay.
- **Possible upgrade**: similarity of at least 60 and a higher overall profile by at least three
  points, optionally within a market-value ceiling. The overall figure **weights each stat by how
  strong the clicked player is at it** (a floor of 0.25 for his or her weak areas), so a winger's
  goals and chances created count far more than clearances. Without this, a defensive midfielder
  with no goals looked like an upgrade on a prolific winger. Each row lists the biggest weighted
  gaps where the candidate is better and weaker, with the per-90 numbers.
- For players linked to the open event data, older event-based matches are shown separately and
  labelled historic.

## Limits

- Per-90 values early in the season rest on a few matches; the page warns below 450 minutes.
- It measures output, not how a player would perform under another coach or in another team.
- Role families come from FotMob, so a player used in a different role (a midfielder at
  right-back) is compared with that family.
- Players who have not played this season, and any page that fails to load, are not in the pool.
