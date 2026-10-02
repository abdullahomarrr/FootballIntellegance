# ADR-003: Provider-independent canonical model

## Context
Providers use incompatible IDs, schemas, coordinates and metric semantics.

## Decision
Adapters map immutable raw responses into canonical dimensions, bridges and facts. Analytics consume canonical contracts only.

## Alternatives
Expose provider JSON directly or make one provider's schema canonical.

## Consequences
Adapters carry more work, but provider replacement and cross-source lineage do not require rewriting product analytics.
