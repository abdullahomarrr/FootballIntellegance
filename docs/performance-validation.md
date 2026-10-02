# Performance validation

Measurement date: 2026-09-29. These are local development measurements, not production
service-level objectives.

## Request-path design

- Player-season totals and per-90 rates are materialized in
  `analytics.mart_player_season_profile` by dbt.
- Position/competition/season percentiles are materialized in
  `analytics.mart_player_metric_percentile`; frontend requests do not recompute percentiles
  from player-match facts.
- Explainable database similarity reads the target's latest qualified profile and the
  precomputed eight-metric percentile population. It computes only the requested target's
  peer ranking, not an all-player similarity matrix.
- Raw event ingestion is checkpointed per match. API list/detail/similarity requests do not
  invoke a provider or rebuild event features.
- Immutable provider responses permit replay without consuming the live provider again.
- Current/live orchestration uses overlap windows rather than full historical refreshes.

## CPU-only endpoint measurements

FastAPI `TestClient` executed 200 successful requests per endpoint on the local Windows
development host under Python 3.14. These figures cover in-process validation and analytics;
they exclude network and database latency.

| Endpoint operation | Median | p95 | Maximum |
|---|---:|---:|---:|
| Tactical fit | 2.578 ms | 3.484 ms | 67.911 ms |
| Development trend | 2.463 ms | 3.898 ms | 29.475 ms |
| In-memory similarity comparison | 2.475 ms | 5.233 ms | 29.621 ms |
| Two-position exact squad optimization | 2.584 ms | 4.187 ms | 29.317 ms |

The maximum values reflect local process scheduling and are retained rather than removed as
outliers. These small deterministic cases do not establish performance for large squad
candidate pools.

## Live PostgreSQL-backed measurements

The rebuilt Docker API was measured over localhost with 25 successful requests per endpoint
against 10,846,880 real events and the final dbt marts. These are development observations,
not an SLO.

| Endpoint | Median | p95 | Maximum |
|---|---:|---:|---:|
| Player list, 20 rows | 48.55 ms | 61.23 ms | 245.76 ms |
| Player seasons | 24.35 ms | 26.48 ms | 26.90 ms |
| Player metrics | 22.33 ms | 43.71 ms | 54.98 ms |
| Explainable similarity | 48.74 ms | 51.37 ms | 54.19 ms |
| Provider match summary | 24.45 ms | 28.70 ms | 31.44 ms |
| Player spatial summary, before index | 481.80 ms | 490.75 ms | 591.82 ms |
| Player spatial summary, after index | 22.62 ms | 31.09 ms | 330.89 ms |

The measured spatial bottleneck led to migration
`012_fact_event_player_spatial_index.sql`. Final `EXPLAIN (ANALYZE, BUFFERS)` used an
index-only scan, read 2,863 player events with 37 heap fetches, and completed in 1.825 ms at
the database layer. The higher HTTP maximum is retained as observed local scheduling/startup
noise rather than discarded.
