# Known limitations

- No API-Football credential is configured, so authenticated 2026/27 coverage and live
  correction behavior cannot be verified or ingested.
- Wyscout Open provides one complete Big Five season (2017/18), not a live feed.
- StatsBomb Open contains four complete Big Five 2015/16 seasons plus many club-focused
  samples; a catalogue row is not automatically a complete league season.
- StatsBomb lineups omit date of birth. Cross-provider player mappings remain separate when
  a name/nationality match lacks enough evidence for safe automatic linking.
- Provider positions are broad in the comparison mart; detailed role comparisons are not
  claimed.
- Attacking direction was checked: over 99% of shots from both providers fall in the attacking
  third in both halves, so locations are team-relative (attacking left to right). Heatmaps and
  threat maps are zone summaries, not tracking data.
- Wyscout has no pressures, recoveries, carries or goal-keeper detail beyond saves. Archetypes
  that need them are marked "limited by provider data", and Wyscout xT excludes carries.
- Where a league-season has fewer than 15 qualified players of a position, percentiles use a
  wider same-provider position pool across competitions and seasons. This is labelled in the
  interface and compares across eras and leagues.
- The same person can exist once per provider. 1,827 people (full name held by exactly one
  StatsBomb and one Wyscout identity) are presented as one profile; 800 also share a club. Facts
  stay keyed by provider so nothing is double-counted, and where both providers cover the same
  club-season the larger sample is shown. The rule can in principle join two different people
  with an identical full name; run `build-person-groups` after identity changes.
- Short display names come from StatsBomb nicknames, Wyscout short names and a grounded LLM pass;
  about 230 long names still show in full until the LLM quota allows another run.
- Research claims come from headlines and Wikipedia lead text by rules. They are noisy,
  unverified, and absence of a claim does not mean absence of a fact.
- A frozen third-party snapshot (derived from Transfermarkt, valuations to 2026-06-12) is loaded
  and labelled as such: 128,913 valuations, 23,144 transfers and 2,725 contract dates linked to
  92.7% of qualified players. Values are crowd-sourced estimates, not fees, and not current. Wages,
  injuries and live contracts remain unavailable.
- Superseded: no approved historical market-value, transfer-fee, wage, contract, or injury dataset is
  present. Valuation training and real budget optimization are blocked by licensed inputs.
- No approved production news feed is available. A fresh GDELT DOC 2.0 check on 2026-09-30
  still returned HTTP 429 from this host. Bluesky public AppView is available on a deliberately
  narrow basis: 100 deduplicated posts, two daily aggregates and one conservatively linked
  player. It is labelled non-representative, public context rather than player-quality evidence.
- The exact squad optimizer is appropriate for small supplied pools; it has no production
  candidate costs or validated fit scores in the current data.
- StatsBomb 360 coverage exists only for selected matches and is not yet a published mart.
- Deployment, production authentication, managed scheduling, and cloud alerting are outside
  this phase.

- Current Premier League players (for example Haaland and Saka) have a stats-tier profile from the
  unofficial public Fantasy Premier League feed, not an event profile. See
  `docs/data_sources/fpl-feed.md`. Other leagues' current players are not covered for free.

- Tournament event profiles (World Cup 2022, Euro 2020/2024, Copa América 2024, AFCON 2023) are
  short samples of at most seven matches. They show style and location evidence but rarely meet
  the 900-minute rule, so they usually have no percentiles or archetype.
- International tournaments from StatsBomb Open are loaded as event data: UEFA Euro 2020 and 2024,
  FIFA World Cup 2022, Copa America 2024 and the 2023 Africa Cup of Nations (about 2,500 player
  records). They are small samples (a handful of matches, under the 900-minute ranking threshold), so
  they have maps, shot maps and pass maps but no percentiles or archetype, and the profile says so.
- Person grouping also uses a shared Transfermarkt ID (exact Reep ID, or a name match that agreed
  99.5% of the time against Reep) to join a player's StatsBomb and Wyscout records when their names
  differ. A record claimed by more than one counterpart is never grouped.

- Current La Liga players have a lighter stats profile from the free Big Ball Sports API tier:
  current season only, no event locations, expected stats or birth dates. About 17 players have a
  current club outside La Liga in the feed, so their club is shown as unclear. Links to older event
  profiles use exact name plus club and cover only a minority of players. Other leagues' current
  players are still not covered. See `docs/data_sources/laliga-stats-feed.md`.

- **FotMob squads and alternatives are for personal use only.** The `/squads` page, the squad
  tables and the alternatives finder read FotMob's public web pages, which FotMob's terms do not
  permit. The source must be removed before any public deployment. See
  `docs/data_sources/fotmob-pages.md`. The finder compares this season's per-90 output only; it is
  not a prediction of fit or performance in another team, and early-season samples are small.

- The default player directory order ("Most popular") ranks by the highest Transfermarkt-snapshot
  market value a player ever had, plus a small editorial boost for well-known older players
  (`FEATURED_PLAYERS` in `repository.py`), and ranks players with under 900 recorded minutes ever
  lower. It is a rough fame ordering, not a measure of quality, and players with no event profile
  (for example Michael Olise) cannot appear in it.
