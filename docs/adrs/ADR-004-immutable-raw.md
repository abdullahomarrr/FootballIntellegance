# ADR-004: Immutable raw storage

## Context
External corrections and schema drift require replay and auditability.

## Decision
Persist every permitted external response before transformation using content checksums, request metadata, ingestion time and pipeline-run identity.

## Alternatives
Transform in memory and retain only canonical rows.

## Consequences
Storage usage increases; reproducibility, reconciliation and recovery improve. Secrets are never placed in object keys or manifests.
