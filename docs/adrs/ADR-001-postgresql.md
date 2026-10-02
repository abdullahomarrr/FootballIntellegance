# ADR-001: PostgreSQL instead of MongoDB

## Context
The platform needs constrained relational grains, temporal joins, provider bridges, dbt models and auditable transactions.

## Decision
Use PostgreSQL for canonical, analytical and operational metadata. Keep raw payloads in immutable object storage.

## Alternatives
MongoDB and document-only storage were considered.

## Consequences
Schema migrations and relational integrity are first-class. Provider JSON must be normalized, while raw JSON remains replayable outside canonical tables.
