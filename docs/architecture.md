# Architecture

## Logical flow

```text
Provider discovery ───────► coverage observations ───────► coverage API/UI
       │
External providers ───────► immutable raw object storage
                                      │
                                      ▼
                           adapter normalization
                                      │
                                      ▼
                     PostgreSQL canonical/bridge/fact layer
                                      │
                                      ▼
                         dbt staging → intermediate → marts
                                      │
                         ┌────────────┴─────────────┐
                         ▼                          ▼
                 analytics/features          quality/lineage
                         │
                         ▼
                       FastAPI
                         │
                         ▼
                 Next.js product
```

## Deployment choices

- **Local Phase 1:** Docker Compose with PostgreSQL and MinIO (or filesystem behind the same object-store interface). A simple Python CLI/scheduler is sufficient initially.
- **Cloud target:** S3-compatible object storage, managed PostgreSQL, containerized ingestion/API, and a managed scheduler. Choose the cloud only when deployment begins.
- **dbt:** canonical facts are inputs; dbt owns transformations and tests, not API extraction.
- **Orchestration:** start with a small explicit job graph. Airflow is deferred until scheduling/backfill complexity demonstrates a need.
- **FastAPI:** reads marts and exposes metadata (`data_as_of`, providers, feature/model version, coverage level).
- **Frontend:** Next.js shell and interactive recruitment/squad demos are implemented; longitudinal views remain coverage-gated until player-match data is licensed.

## Incremental/live path

1. Discover the current competition/season and checkpoint.
2. Fetch changed/new fixtures within an overlap window to catch provider corrections.
3. Write raw payload plus manifest atomically.
4. Idempotently upsert provider staging rows keyed by provider ID and source update time.
5. Resolve identities; quarantine ambiguity.
6. Build player-match facts and reconcile season totals.
7. Run dbt models/tests for impacted partitions.
8. Snapshot live player-season profiles.
9. Refresh percentiles/similarity only for compatible populations.
10. Publish the latest successful `data_as_of`; never advance freshness after a partial failure.

## Reliability and observability

Record per run: provider, endpoint, parameters hash, pages, rows, bytes, quota headers, retries, raw checksum, inserted/updated/quarantined counts, schema drift, test results, start/end time and code commit. Alert on stale live partitions, sudden row-count changes, mapping ambiguity, reconciliation variance and quota exhaustion.

## Security and provenance

Secrets stay server-side in environment-backed secret storage. Raw URLs and logs redact keys. API input is validated; deployment-edge rate limiting is required when the local single-user API becomes network-facing. Every product value carries a path to source run, raw object, transformation version and model/feature version.

## Architecture decisions

- PostgreSQL over MongoDB: relational grains, constraints, joins and dbt compatibility dominate.
- Player-season-team-competition as primary analytical grain: preserves transfers and competition context.
- Immutable raw layer: replay, audit and schema-change recovery.
- Provider adapters: provider replacement does not rewrite analytics.
- Coverage as data: prevents fabricated visualizations and false precision.
- No Airflow/MLflow yet: premature before stable ingestion and real experiments.
- Derived analytics are stored separately from provider facts and carry a model version; the current xT implementation is a transparent location-value baseline, not provider xG.
