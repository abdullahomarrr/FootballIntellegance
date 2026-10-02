# Operations

## Local stack

`docker compose up --build` starts PostgreSQL, applies every idempotent SQL migration through
the one-shot `migrate` service, then starts FastAPI and Next.js. This upgrades existing volumes
without deleting historical data; PostgreSQL's initialization hook remains the fresh-volume
bootstrap. The API does not start when a migration fails.

## Pipeline observability

Every scheduled job must create a `pipeline_run` row before external I/O and terminate it as `SUCCEEDED`, `FAILED`, or `PARTIAL`. Record rows read/written/quarantined, quota use, error summary and commit SHA. Product freshness advances only after a successful mart build.

## Alerts

Alert on stale live partitions, failed or long-running jobs, provider schema drift, reconciliation variance, unresolved-identity spikes, quota exhaustion, and unexpected row-count changes. Do not alert merely because an intentionally unavailable capability remains unavailable.

## Recovery

Raw objects are immutable and content-addressed. Replay normalization from the recorded raw URI and schema version. Idempotent provider-event upserts permit safe retry. Never advance `data_as_of` after a partial failure.
