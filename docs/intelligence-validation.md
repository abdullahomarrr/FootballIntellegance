# Intelligence layer validation

Run date: 2026-10-01. Stack: PostgreSQL 17 (real warehouse: 10.8M events, 8,389 provider
identities), FastAPI, Next.js dev server, driven in the built-in browser pane at 1440×900 and
375×812.

## What was validated, and how

Every capability below was exercised end to end (database → dbt mart → API → rendered page) on
real players, not fixtures. `tests/test_intelligence_layer.py::test_real_warehouse_…` repeats the
database-level checks automatically and skips only when Postgres is unreachable.

| Capability | Where it is visible | Evidence |
|---|---|---|
| Position-specific metric families | Profile → Event intelligence radar and metric grid | 15 outfield and 7 goalkeeper metrics; goalkeeper and outfield populations never mix (dbt test) |
| Expected threat (xT) | Profile → stat tile, radar axis, xT zone map | `xt_added_per_90` ranked per position; map sums completed pass and carry threat by start zone |
| Goalkeeper analytics | Profile (GK) → save %, distribution %, long-pass %, distribution map | Schmeichel 2015/16: 76.6% saves, 39% distribution, long-ball map of 150 passes |
| Real heatmaps | Profile → On-pitch behaviour | 12×8 density with All / Passes / Carries / Defensive layers computed in SQL |
| Shot map | Profile → On-pitch behaviour | xG-sized markers; All / Goals / Big-chance filters; Wyscout goals read from tag 101 |
| Pass map | Profile → progressive passes (outfield) or long passes (GK) | Start-to-end arrows, completed vs not completed |
| Archetypes with secondary profile | Profile → Scouting interpretation | Position-specific catalogue; primary, secondary, clarity (clear / blended / limited / weak), fit bars |
| Archetype discovery | Players → Discover by playing style | Ranked search per position and style, evidence chips per result |
| Contextual similarity | Profile → Similar players; Recruitment search | Like-for-like cohort, or a labelled pooled population; per-metric dot plots |
| Tactical context | Profile → How the team plays | Squad style axes vs the player, what he adds and where the squad carries the load |
| Role fit | Profile → Fit against your saved briefs; Recruitment | Weighted fit with drivers and gaps; refuses briefs the data cannot cover |
| Explainable scouting report | Profile; "Copy scouting brief" | Summary, strengths, questions, caveats, team context, role fit as copyable text |
| Source-linked current context | Profile and Market | Claims with quote, source URL, retrieval time and an "Unverified public estimate" badge |
| One profile per person | Profile season picker, directory, similar players, discovery | StatsBomb and Wyscout records of 1,827 people are presented together; Messi shows 19 seasons, picker re-scopes every panel |

## Browser matrix

All rows rendered the archetype, radar, comparison-scope note, heatmap layers, xT map, pass
map, similar players with difference bars, research claims and the copy action with no partial-load
notice.

| Player | Position / provider | Archetype shown | Notes |
|---|---|---|---|
| Kylian Mbappé (2022/23) | FW · StatsBomb | Penalty-area goal threat (secondary: dribbling ball-carrier) | Thin league cohort → pooled population, labelled. Peers: Suárez, Ronaldo, Villa, Benzema |
| Toni Kroos (2015/16) | MD · StatsBomb | Deep-lying playmaker (fit 96) | Peers: Busquets, Modrić |
| Virgil van Dijk (2015/16) | DF · StatsBomb | Ball-playing defender | 7 research claims |
| Kasper Schmeichel (2015/16) | GK · StatsBomb | Shot-stopper | GK radar, GK stat tiles, distribution map |
| Thibaut Courtois (2017/18) | GK · Wyscout | Distributing keeper, no standout profile | Wyscout lacks claims/goals-conceded detail; disclosed |
| N'Golo Kanté (2017/18) | MD · Wyscout | Deep-lying playmaker, "limited by provider data" | Ball-winning profile is secondary at 77; Wyscout has no recoveries or pressures |
| Lionel Messi (2017/18) | FW · Wyscout | Creative attacker, blended | 26 goals now appear on the shot map; links to his StatsBomb record |
| Harry Kane (2015/16) | FW · StatsBomb | Penalty-area goal threat | Like-for-like cohort of 85 forwards |
| Paul Pogba (2015/16) | MD · StatsBomb | Box-to-box carrier (secondary: attacking midfielder) | Blended style team context |

Other routes were exercised too: recruitment search from a reference player (Kroos → Busquets,
Gabi, Modrić), compare (Kroos vs Busquets), shortlists, squad coverage, market, coverage and the
landing page. `next build` produces all ten routes.

## Face-validity of discovery

Rankings were read against football knowledge, not just checked for non-emptiness:

- Defenders, **Ball-playing defender**: Mascherano, Piqué, Tapsoba, David Luiz, Lenglet, Umtiti.
- Midfielders, **Ball-winning midfielder**: Kanté, Gana Gueye, Gori, Fernández, Kankava, Kirchhoff.

## Defects found by validation and fixed

1. **Stale warehouse.** The database predated the latest dbt models and migration 014, so the
   player list, intelligence and squad pages failed. Marts were rebuilt and 014 applied.
2. **Flagship player had no intelligence.** Mbappé's 2022/23 league sample had too few qualified
   forwards, so every metric was dropped. Percentiles now fall back to a clearly labelled pooled
   provider population, and similarity compares pooled targets only against pooled peers.
3. **Defensive duels were zero or missing for everyone.** The metric matched `'%defensive%'`, but
   StatsBomb calls them "Tackle" and Wyscout "Ground defending duel". Fixed in the mart and the
   profile query.
4. **Provider mixing.** Local cohorts could combine Wyscout and StatsBomb counts that are
   defined differently. Cohorts are now partitioned by provider.
5. **Overconfident archetypes.** Kanté was labelled a playmaker with no warning. Archetypes now
   state which profiles could not be assessed and why, and the chip reads "Limited by provider data".
6. **Wyscout goals invisible.** Wyscout records goals as a tag; the shot map showed none.
7. **Attacking direction caveat was overly conservative.** Over 99% of shots from both providers
   fall in the attacking third in both halves, so maps are labelled left-to-right with that
   evidence instead of "not normalized".
8. **Port conflict and server drift.** A stale API worker kept serving old code; the dev server
   now needs a manual restart on Windows/OneDrive because file-watch reload is unreliable here.

## Not validated

- The optional LLM claim extractor (`ANTHROPIC_API_KEY`) is tested only with a fake caller and
  grounding checks; no live key was available. The rules extractor is what ran.
- Current-season (2026/27) player performance does not exist in the open event data.
- Market values, fees, wages, contracts and injuries beyond what public sources state in text.

## Follow-up (same day): one profile per person, short names

- Similar players and discovery returned the same person once per season; they now return one row
  per person (best season). The directory already deduplicated by name.
- A season picker on the profile re-scopes scouting report, heatmaps, peers, team context and
  role fit to any club-season; the development trend spans all seasons.
- Bug found while testing a many-season player: development trends silently dropped every season
  with no `start_date` (23 of 24 seasons), so Messi had no trend at all. Dates now derive from the
  season label; his trend covers 18 qualified seasons.
- Display names shortened for all players (nicknames, Wyscout short names, grounded LLM pass).

## Market layer (same day)

- Frozen third-party snapshot loaded and linked to 92.7% of qualified players (name + birth date,
  then name + nationality + position). Valuations, transfers and contract dates appear on the
  profile, the recruitment filter and the squad budget planner, always labelled as historical and
  not a fee.
- A time-boxed valuation experiment (train before 2017/18, test after) improved on a cohort-median
  baseline by about 16% (mean error EUR 10.3m vs 12.2m), but its 80% interval covered only 47% of
  real values because market values inflate over time. It was not shipped as a valuation.
- A "performance vs value" gap view was built and then removed: the usable season and position
  cohorts were too thin to be worth keeping.

## Current Premier League stats tier (same day)

- Haaland, Saka, Palmer and every current Premier League player now have a stats profile (totals,
  xG/xA, injury and availability news, four or more past seasons, gameweek table, rankings against
  current peers). Verified in the browser for Haaland: 450 minutes, 5 goals, 4.42 xG, ranked among
  21 forwards.
- Event profiles of players who are also in the current feed (for example Declan Rice's 2017/18
  profile) show a live availability banner and link to the stats profile.
- The directory merges stats-tier results under event results, and a coverage note plus a clear
  "not in our data" message replace blank results.
- Reep's ID crosswalk audited the Transfermarkt links (99.5% name-and-nationality agreement) and now
  overrides them with exact IDs for 2,491 players; the qualified link rate rose from 92.7% to 95.8%.

## Follow-up: tournament event data

- StatsBomb Open also publishes full-event data for five recent tournaments: World Cup 2022 (64
  matches), Euro 2020 (51), Euro 2024 (51), Copa América 2024 (32) and AFCON 2023 (52). All were
  loaded with the existing backfill and player-match loaders; no new parser was needed.
- This gives event profiles (heatmaps, xT, pass and shot maps) to many current players whose club
  seasons are not open, for example Saka (654 min, Euro 2024; 293 min, World Cup 2022).
- Tournament samples are small (seven matches at most), so every one is labelled "tournament
  sample" in the season picker and a banner. They are not mixed into club-season percentiles
  unless they reach the 900-minute qualification, which almost none do.
- Verified on Saka: three tournament seasons in the picker, all four spatial layers, and market
  values, transfers and contract linked through name and nationality.

## Tournament event data (same day)

- Loaded Euro 2020, Euro 2024, World Cup 2022, Copa America 2024 and AFCON 2023 from StatsBomb Open
  (about 200 matches). Verified for Saka (654 minutes at Euro 2024), Bellingham, Foden, Rice, Kane
  and Palmer: real event data with maps, labelled as a tournament sample.
- Saka's current Premier League stats profile now links to his event profile, and Foden's old
  Wyscout record and tournament record are one person (1,991 people grouped).

## Follow-up: current La Liga stats tier

- Source: free tier of the Big Ball Sports API (`docs/data_sources/laliga-stats-feed.md`). 69
  finished 2026/27 matches were pulled (about 70 requests) and summed per player: 457 players, 252
  with enough minutes to rank.
- Cross-checked against the provider's season leaderboard: Raphinha, Yamal and Mbappé match on
  goals and assists; minutes match within a few from stoppage-time rounding.
- Two data traps found while testing: `pass_accuracy` is a count of completed passes, and a line's
  team is the player's current club, not the side they played for. Both are handled and tested.
- Browser-validated on a forward (Raphinha, ranked against 37 forwards), a goalkeeper (David
  Soria, ranked against 21 goalkeepers, with an older event profile linked) and a player whose club
  is unclear (Dani Ceballos, shown honestly as unranked and club unclear). Yamal links to his Euro
  2024 event profile by exact name and club.
- Not validated: injuries from this feed are not used; the paid tier's history is not available.

## Follow-up: club squads and the alternatives finder

- All 96 clubs of the five leagues for 2026/27 are loaded (Premier League 20, La Liga 20, Serie A
  20, Bundesliga 18, Ligue 1 18): 2,747 players, 360 linked to our older event records on birth
  date plus name. Player pages were warmed for the 1,924 players with a match rating this season
  (no failures); 1,563 have enough data to sit in the comparison pool.
- First version flaw, found by reading real results: with every stat weighted equally, Yamal's
  "upgrades" included a midfielder with no goals, because clearances and long-ball accuracy offset
  goals and chances created. Fixed by weighting stats toward the clicked player's strengths and by
  dropping noisy rate stats; Yamal's upgrades fell from eight to one (Olise, +3.5), with honest
  weaker-at lists.
- Sanity checks: Bellingham and Rodri have no upgrades (they top their families on these numbers);
  Haaland's include Mbappé, Lautaro Martínez and Schick; Saka's include Olise; Reece James's include
  Nuno Mendes and Ridle Baku. Emi Martínez has no clearly higher-ranked similar keeper.
- Browser-validated on Sunderland, Chelsea and Barcelona squads (injury flags, event-profile
  badges, values), and on player panels for Danso, Reece James and Yamal (heat map, shot map,
  per-90 groups, ranked alternatives, market-value ceiling).
- Not validated: results depend on early-season samples (the page warns below 450 minutes), and
  the source is for personal use only (see `docs/data_sources/fotmob-pages.md`).
