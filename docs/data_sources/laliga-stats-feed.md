# Current La Liga stats feed (Big Ball Sports API, free tier)

## What it is

A current-season stats tier for La Liga players, built from the free tier of the Big Ball Sports
API (`https://api.bigballsdata.com`, key in `BIGBALLS_API_KEY`). It exists because open event data
does not cover recent club seasons, so most current La Liga players have no event profile.

## What is pulled

- `GET /v1/matches?sport=football&league=laliga&season=<start year>&status=finished` once an
  hour, to list finished matches (69 at the time of writing).
- `GET /v1/stored/matches/{id}/stats` once per finished match. A finished match never changes, so
  each response is cached on disk (`data/external/laliga/matches/`, git-ignored) permanently. A
  cold pull is about 70 requests; later refreshes fetch only newly finished matches.

Per-player lines are summed into season totals and per-90 rates, then ranked within position
(goalkeepers use their own metric set) once a player passes a minutes floor of 40% of the busiest
team's matches played (252 minutes after seven rounds).

## Limits of the free tier

- Current season only; one season back needs the paid plan.
- 500 requests a day and 100 a minute. The loader spaces requests 0.7 s apart.
- No event locations, no expected stats, no birth dates, no career or transfer history, no
  headshots. Injury reports exist but are not used here.

## Findings that shaped the code

- `pass_accuracy` is the number of **completed passes**, not a percentage (Rodri: 66 of 73). Pass
  completion is computed as completed divided by total passes, and only ranked from 100 passes.
- A line's `team_name` is the player's **current** club record, not the side they played for in
  that match. About 17 players show a club outside La Liga (loans, transfers, national teams, or
  none). Their stats are kept but their club is shown as "Club unclear" and they are not linked.
- Cross-check against the provider's own season leaderboard: Raphinha 555 min, 12 goals, 3
  assists; Yamal 581 min, 7 goals, 4 assists; Mbappé 7 goals, 2 assists. Minutes differ by at most
  a few from stoppage-time rounding (Mbappé 634 here, 630 on the leaderboard).

## Linking to older event profiles

No birth dates, so links use exact name plus club, only when exactly one of our players fits:

1. the full feed name matches one of our name variants and that player's latest Transfermarkt
   contract club matches the La Liga team; or
2. every word of the feed name appears in one of our longer legal names, among players whose
   contract club matches the team, and exactly one fits.

On the pull of 1 October 2026, 54 of 457 players linked, all spot-checked as the right person
(for example Yamal to Lamine Yamal Nasraoui Ebana, Vinícius Júnior to his full legal name).
Players we cannot link simply have no "older event profile" link.

## Licence

The free tier's terms were not reviewed in full. The data is used read-only, cached, attributed on
every page, and not republished in bulk. Revisit before any public deployment.
