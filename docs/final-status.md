# Final status register

Assessment date: 2026-10-01. This register reflects the final local validation run.

Allowed states are: `COMPLETE`, `COMPLETE BUT DATA-LIMITED`, `BLOCKED BY CREDENTIALS`,
`BLOCKED BY PAID/LICENSED DATA`, and `OPTIONAL FUTURE WORK`.

| Feature | Status | Evidence and boundary |
|---|---|---|
| Immutable raw ingestion and provenance | COMPLETE | Content-addressed storage, manifests, checksums, replay and corruption tests |
| Wyscout 2017/18 Big Five event history | COMPLETE | 1,826 matches, 3,071,392 events and 50,584 player-match rows |
| StatsBomb open Big Five sample seasons | COMPLETE BUT DATA-LIMITED | 23 catalogue seasons and 652 matches were replayed under the corrected coordinate policy |
| StatsBomb open full 2015/16 seasons | COMPLETE BUT DATA-LIMITED | All four legitimately available full seasons are loaded: La Liga 380, Ligue 1 377, Premier League 380 and Serie A 380 matches |
| Canonical identity and provider bridges | COMPLETE BUT DATA-LIMITED | Conservative audited resolution is implemented; weak name-only cross-provider matches remain unmerged |
| Player-season and percentile marts | COMPLETE BUT DATA-LIMITED | Expanded real warehouse contains 12,219 profiles, 3,287 at 900+ minutes, and all 20 dbt nodes/tests pass |
| Advanced event intelligence | COMPLETE BUT DATA-LIMITED | Fifteen outfield metrics (including expected threat) and seven goalkeeper metrics (save %, distribution, long-pass accuracy, claims, sweeping) are calculated from real events with position-specific, provider-aware populations and direction-adjusted percentiles. Thin league cohorts fall back to a labelled pooled provider population. Wyscout lacks pressures, recoveries and carries, so some metrics are unavailable for it and disclosed |
| Spatial intelligence and explainable similarity | COMPLETE BUT DATA-LIMITED | Real 12×8 heatmaps with pass / carry / defensive layers, an expected-threat zone map, a progressive-pass or goalkeeper distribution map, and a filterable xG shot map. Attacking direction verified (99%+ of shots in the attacking third for both providers). Similarity reports overlap, closest evidence, trade-offs and confidence, never mixes cohorts, and is separate for goalkeepers |
| Explainable scouting and tactical role fit | COMPLETE BUT DATA-LIMITED | Position-specific archetype catalogue with a secondary profile, clarity rating and per-profile fit; team style context (what the player adds and what the squad carries); weighted role fit against saved briefs; archetype discovery search; copyable scouting brief. All outputs are evidence-led and marked for human review |
| Observed player development | COMPLETE BUT DATA-LIMITED | Direction-normalized advanced-event percentiles are tracked across qualified season samples within the same position family. The profile exposes annual movement, evidence-minutes, confidence and context while explicitly refusing to treat the descriptive slope as a forecast |
| Tournament event data | COMPLETE BUT DATA-LIMITED | World Cup 2022, Euro 2020/2024, Copa América 2024 and AFCON 2023 (250 matches) give event profiles to many current players; samples are at most seven matches and labelled as such |
| Current stats tiers (Premier League, La Liga) | COMPLETE BUT DATA-LIMITED | Premier League from the public FPL feed; La Liga from the free Big Ball Sports API tier (69 matches summed into 457 players). Totals and per-90 rankings only, no event locations; see docs/data_sources |
| Club squads and alternatives finder | COMPLETE BUT DATA-LIMITED, PERSONAL USE ONLY | All 96 clubs in the top five leagues (2,747 players) from FotMob's public pages; per-player stats, heat maps and shot maps; similar players and upgrades across leagues by role family. Source is not licensed for public use; see docs/data_sources/fotmob-pages.md |
| Current 2026/27 fixtures and results | COMPLETE BUT DATA-LIMITED | OpenFootball provides 2,364 fixtures across seven leagues, including 353 completed results; current player-performance and squad feeds still require an approved provider |
| Historical/current market values, fees and contracts | BLOCKED BY PAID/LICENSED DATA | No approved source with adequate historical as-of observations is available |
| Trained valuation model and calibrated uncertainty | BLOCKED BY PAID/LICENSED DATA | Leakage-safe training/evaluation boundary exists, but legitimate labeled targets do not |
| Current-context research | COMPLETE BUT DATA-LIMITED | On-demand, allowlisted retrieval (Google News headlines and Wikipedia) with structured claims for injury, contract, transfer, market value, club and form. Each claim carries a verbatim quote, source URL, retrieval time and an unverified-estimate badge, and never affects performance scoring. Extraction is rule-based; an optional LLM extractor with a grounding check is implemented but untested against a live key. Reliable market values, fees and contracts still need licensed data |
| Public fan/social sentiment | COMPLETE BUT DATA-LIMITED | 100 real public Bluesky AppView posts are retained as immutable observations and exposed as two daily aggregates for one conservatively linked player; explicitly context-only and not representative |
| Recruitment roles, shortlists and real-data search | COMPLETE BUT DATA-LIMITED | Real advanced-event alternatives can be ranked by similarity plus role fit and carried into persistent shortlists with rank, stage, rationale and a selection-time evidence snapshot; refreshed archetype, coverage, strongest signal and review question remain visibly separate |
| Squad planning | COMPLETE BUT DATA-LIMITED | Active role-backed shortlists now populate position coverage, pipeline readiness and visible gaps. Costs, wages and medical availability remain deliberately excluded without legitimate current data; the exact optimizer remains tested for supplied valid inputs |
| Comparison | COMPLETE BUT DATA-LIMITED | The comparison route now uses the same advanced event mart as profiles and recruitment, includes peer populations and archetypes, and refuses to collapse goalkeeper and outfield evidence into one rating |
| API and web application | COMPLETE BUT DATA-LIMITED | Python/API tests, strict typing, the ten-route production build and a browser pass over nine real players across all position groups and both providers pass; see `docs/intelligence-validation.md`. Docker data was preserved through an engine failure and the warehouse rebuilt |
| Cloud deployment, managed scheduling and production auth | OPTIONAL FUTURE WORK | The specification deliberately leaves the deployment target and multi-user operating model unspecified |

## Final local verification

Ruff, strict mypy, the full Python suite (including a real-warehouse integration test) at over
84% coverage, the dbt build with all data tests, frontend type checking and the ten-route
production build passed on 2026-10-01. The browser validation matrix, defects found and
fixes are recorded in `docs/intelligence-validation.md`. External data limits still require
credentials, licensed data, or a future deployment decision.
