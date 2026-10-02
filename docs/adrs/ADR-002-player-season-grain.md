# ADR-002: Player-season-team-competition analytical grain

## Context
A single player-season row loses loans, transfers and cross-competition differences.

## Decision
The primary longitudinal profile grain is player × team × competition × season, with player-match facts beneath it.

## Alternatives
One career vector or one row per player-season.

## Consequences
Transfers remain explicit and comparisons require a declared population. Career views aggregate deliberately rather than accidentally.
