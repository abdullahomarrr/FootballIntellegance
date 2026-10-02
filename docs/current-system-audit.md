# Current system audit

Audit date: 2026-09-30. Status values are exactly those required by the specification:
`WORKING`, `PARTIAL`, `PLACEHOLDER`, `MOCK`, `BROKEN`, `NOT IMPLEMENTED`, or
`BLOCKED BY CREDENTIALS`.

| Subsystem | Status | Verified evidence | Remaining boundary |
|---|---|---|---|
| Repository/tooling | WORKING | Locked Python environment, Next.js, PostgreSQL migrations, dbt, Compose and CI are present; formatting, lint, typing, tests and web build execute | Keep evidence current |
| Frontend player intelligence | WORKING | Canonical profiles now surface position-specific advanced metrics, evidence-led archetypes/reports, real event heatmaps, shot maps, current-context links and goalkeeper-specific panels | Latest changes await renewed browser validation |
| Recruitment frontend | WORKING | Real advanced similarity, feature trade-offs, reusable role weights, role fit, recommendation score and search→shortlist handoff are implemented without fictional candidates | Age/value constraints remain limited by legitimate source coverage |
| Squad frontend | PARTIAL | Active role-backed shortlists populate position coverage, decision readiness and visible gaps without synthetic prices | Real costs, wages, medical availability and current squads require licensed data |
| Market frontend | PARTIAL | Real Bluesky aggregates, permitted-text analysis, source-linked live headline metadata and genuine stored cost observations are separated from performance evidence | Durable news bodies and reliable current cost/contract facts require approved sources |
| FastAPI | WORKING | Canonical players, seasons, metrics, spatial, similarity, market gates, roles, shortlists, comparison and optimizer contracts execute | Production auth is deployment scope |
| PostgreSQL canonical model | WORKING | Dimensions, provider bridges, matches, events, player-match, market/news/social schemas and migrations execute | Gated facts remain empty by design |
| Wyscout Open ingestion | WORKING | Complete 2017/18 Big Five: 1,826 matches and 3,071,392 accepted events; idempotent replay evidence | No other Big Five seasons exist in this release |
| StatsBomb Open ingestion | WORKING | All 23 sample seasons were replayed and all four full 2015/16 Big Five seasons loaded; 2,169 StatsBomb matches have events, checkpoints, identities and player-match facts | Coverage remains limited to the public catalogue |
| API-Football | BLOCKED BY CREDENTIALS | Current adapter, retry boundary, coverage discovery tests and documentation exist; no key is configured | Authenticated 2026/27 discovery and ingestion cannot run |
| Immutable raw storage | WORKING | Atomic content-addressed objects, checksums, terms/schema metadata and replay tests | Cloud storage is deployment scope |
| Coordinate normalization | WORKING | Provider raw coordinates and 105×68 transforms are tested; out-of-plane StatsBomb points retain raw event and null normalized location | Attacking direction is not universal |
| Player identities | PARTIAL | Conservative cross-provider scorer, provider bridges, review queue and audited overrides execute at scale | StatsBomb lacks DOB, so uncertain cross-provider people are intentionally not merged |
| Team/competition/season identities | WORKING | Exact-team bridge reuse, explicit Big Five competition aliases and `YYYY/YY` season normalization are tested | Fuzzy team aliases require review data |
| Player-match facts | WORKING | Wyscout lineup/substitution and StatsBomb lineup-interval loaders create real facts; the four full seasons added 42,096 rows with zero unresolved participants | Coverage follows public sources |
| dbt player-season analytics | WORKING | Existing profiles now feed eighteen provider-aware advanced metrics, separate goalkeeper/outfield families, position percentiles and a population-variation test | Broader/current history requires new authorized sources |
| Similarity | WORKING | Advanced-event percentile distance reports overlap, confidence, closest evidence and largest trade-off; role fit changes recommendation order and goalkeepers use a separate feature family | Independent club-analyst endorsement remains outside engineering evidence |
| Spatial intelligence/xT | PARTIAL | Millions of real located events now produce contextual 12×8 density maps and xG-sized shot maps, alongside the versioned xT baseline | Attacking direction is provider-relative and learned/360 tactical models remain data-limited |
| Development | PARTIAL | Real multi-season profiles and chronology-aware trend baseline exist | Cross-provider identity gaps reduce some player histories |
| Tactical fit/archetypes | PARTIAL | Deterministic evidence-citing reports, position-aware archetypes and user-weighted role fit are surfaced in the product | Detailed analyst-authored role ontology and external validation remain absent |
| Recruitment roles/shortlists | WORKING | Persistent workflows now retain rank, stage and rationale while surfacing each candidate’s archetype, role-fit coverage, strongest signal and main review question | Removal and user ownership are outside current local scope |
| Squad optimizer | PARTIAL | Exact hard-budget, unique-player, position-need solver and infeasibility tests work | Legitimate production costs and fit scores are unavailable |
| Transfers/market values/injuries | BLOCKED BY CREDENTIALS | Nullable canonical schemas, fee parser and fail-closed APIs exist | No approved licensed source or key is available |
| Valuation model | BLOCKED BY CREDENTIALS | Temporal contract and leakage tests reject invalid use; API returns no estimate | No licensed as-of target dataset, so training/metrics/intervals cannot exist |
| Current-context research/news | PARTIAL | Public Google News RSS headline metadata is linked to publisher sources without retaining article bodies; canonical full-news ingestion remains gated | Approved credential/retention rights are required for durable/full-text news |
| Social sentiment | PARTIAL | Real retained public Bluesky aggregates and user-text lexicon are labelled external context only with sample/date caveats | Coverage is narrow and no representative labelled evaluation corpus exists |
| Orchestration/backfills | WORKING | Dependency helpers, overlap windows, per-match atomic checkpoints, retry after transient Windows locks and CLI commands are tested | Managed scheduler is deployment scope |
| Observability | PARTIAL | Pipeline schema, reports, checkpoints and run helper exist | Not every bulk command writes `pipeline_run`; alerts are deployment scope |
| Data quality | WORKING | Quarantine/null semantics, unique/range tests, dbt tests, checksums, idempotency and malformed-source regression tests exist | Final reconciliation report follows complete backfill |
| API tests | WORKING | TestClient contracts plus live player, evidence, similarity and persistent shortlist journeys pass | Production load testing depends on deployment target |
| Browser E2E | PARTIAL | Earlier primary routes and real Mbappé/Schmeichel intelligence passed desktop browser checks; production build still covers ten routes | Re-run every route and mobile workflow after the local Docker engine is restored |
| ML experiment tracking | NOT IMPLEMENTED | No model is trained, so no experiment exists | Add only after licensed target approval |
| Local containers | BROKEN | A prior rebuilt PostgreSQL/API/web baseline passed health and live journeys | Docker Desktop currently cannot start its Linux engine because its internal inference socket is inaccessible; application code is not the reported failure |
| Documentation | WORKING | Required audits, methodology, limitations, performance, sanity, final status and 24 evidence answers exist with final database counts | Keep synchronized with future data refreshes |

## Sequencing conclusion

Open catalogue implementation continues to pass static and automated checks. Credentials and
licensed targets remain external gates for current-season performance, market valuation and
durable news capabilities; the application exposes those limits rather than fabricating output.
Final local validation is not complete until Docker and the browser journeys are re-run.
