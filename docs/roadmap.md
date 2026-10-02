# Roadmap: Milestone 1

## Exact first data combination

Implement in this order:

1. **Wyscout open 2017/18 Big Five** for a complete, cross-league event normalization fixture.
2. **StatsBomb Open Data** for richer schema/xG and multi-season variation, beginning with Big Five catalogue discovery and match-count reconciliation.
3. **API-Football Pro validation month** for broad historical and live 2026/27 coverage, only after the adapter/raw/coverage foundations exist.
4. **football-data.org free feed** as an independent fixture/result control if API reconciliation shows value.

Why: open datasets let the platform build and test raw storage, canonical IDs, coordinates and event transformations without spending quota. API-Football is the strongest low-cost broad/live candidate on published endpoint breadth, but its seasonal depth is not proven; therefore the first paid work is discovery, not a blind full backfill.

## Sequential engineering tasks

Each task should merge only after its acceptance criteria pass.

### M1.1 Repository foundation

- Python package with locked dependencies, Ruff, mypy and pytest.
- Docker Compose PostgreSQL plus object-store interface.
- `.env.example`, secret redaction and structured logging.
- CI for lint, typecheck and unit tests.

Acceptance: clean checkout starts dependencies and runs one smoke test; no credential is committed.

### M1.2 Raw object contract

- Define `RawObjectManifest` and deterministic partition/key convention.
- Implement atomic write, SHA-256 checksum and replay reader.
- Add fixture payloads rather than consuming API quota in tests.

Acceptance: identical payload is idempotent; corrupt payload/checksum is detected.

### M1.3 Coverage subsystem

- Create migrations for `provider_coverage_observation`.
- Implement source-independent capability vocabulary.
- Build Markdown/CSV report generator from the table.

Acceptance: this audit matrix can be represented without collapsing `UNKNOWN` into `UNAVAILABLE`.

### M1.4 StatsBomb catalogue adapter

- Fetch and persist `competitions.json` raw.
- Normalize competitions/seasons and count match files.
- Compare observed matches with expected league fixture counts; label partial coverage.

Acceptance: repeatable Big Five catalogue report with checksums and no claim of completeness before reconciliation.

### M1.5 Canonical event foundation

- Define event enums plus raw qualifier preservation.
- Implement StatsBomb 120×80 and Wyscout 0–100 coordinate adapters to 105×68 metres.
- Preserve raw coordinates and orientation metadata.

Acceptance: boundary/missing/direction tests pass; round-trip provenance remains available.

### M1.6 Wyscout open adapter

- Persist collection/file metadata and license metadata.
- Ingest competitions, teams, players, matches and a small event partition.
- Normalize event/sub-event/tag dictionaries.

Acceptance: selected match event counts reconcile with raw; unknown tags survive in qualifiers.

### M1.7 Canonical dimensions and bridges

- Create player/team/competition/season/match dimensions and provider bridges.
- Implement deterministic player candidates, conservative fuzzy scoring and review queue.
- Add version-controlled manual override format.

Acceptance: diacritics/alias/collision/transfer test cases pass; ambiguous João Pedro records do not auto-merge.

### M1.8 Authenticated API-Football discovery

- Add plan/terms metadata and quota telemetry.
- Query leagues/coverage rather than hardcoding seasons.
- Persist every Big Five season/capability observation.
- Sample fixtures, players, fixture-player stats, transfers and injuries across old/recent/live seasons.

Acceptance: generated coverage matrix replaces `?` with evidence where possible and includes raw response links/checksums.

### M1.9 Provider go/no-go review

- Calculate backfill calls, wall time and monthly cost.
- Quantify field nullness and player/minute reconciliation variance.
- Confirm persistence/derived-use/demo rights in accepted terms.

Acceptance: written decision to proceed, narrow scope, switch provider or request commercial quote.

### M1.10 Broad canonical ingestion

- Implement checkpointed, paginated, retry-safe ingestion for approved endpoints.
- Upsert provider staging; quarantine schema drift.
- Build canonical match, player-match and player-team-season facts.

Acceptance: one league across at least three seasons plus live 2026/27 can be queried by player/season/competition/team.

### M1.11 dbt longitudinal marts

- Staging, intermediate and player-season models.
- Uniqueness, relationships, accepted values, null-rate and freshness tests.
- Reconcile summed player-match minutes to provider season totals with a documented tolerance.

Acceptance: tested longitudinal query and reproducible `data_as_of` metadata.

### M1.12 Live update and snapshots

- Overlap-window incremental job.
- Player-season daily/weekly snapshots.
- Failure-safe freshness publication and quota monitoring.

Acceptance: replaying a fixture correction changes the current mart, preserves the prior snapshot and does not duplicate facts.

## Current implementation status

The repository now includes the raw/canonical foundations, open-data discovery, canonical events, conservative identity handling, dbt marts, a verified match vertical slice, similarity, recruitment filtering, exact small-pool squad optimization, FastAPI, Next.js, quality quarantine rules, temporal snapshot tables and a versioned xT baseline. API-Football authenticated discovery code is implemented but cannot truthfully replace unknown coverage without credentials and accepted terms.

## Remaining external gates

- Broad historical and live 2026/27 ingestion requires an approved provider key, plan and terms validation.
- Valuation training requires a licensed point-in-time market-value target; Transfermarkt scraping is prohibited.
- Production news/social ingestion and sentiment require approved APIs and retention/derived-use rights.
- Airflow, Kubernetes and MLflow remain deferred until operational scale or experiment volume justifies them.
