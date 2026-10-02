# ADR-006: Coverage-tier architecture

## Context
Broad match statistics, spatial events, market context and live data do not cover identical seasons or players.

## Decision
Record capability by provider × competition × season and expose coverage level/confidence with outputs. Models declare required features and reject incompatible comparisons.

## Alternatives
Assume a provider-wide coverage level or impute missing metrics as zero.

## Consequences
Some product panels disable gracefully. The system avoids false precision and can enrich only the seasons legitimately covered.
