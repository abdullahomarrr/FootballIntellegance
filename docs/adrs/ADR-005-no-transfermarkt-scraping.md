# ADR-005: No unauthorized Transfermarkt scraping

## Context
Historical market values are useful targets, but technical accessibility does not establish reuse rights.

## Decision
Do not scrape Transfermarkt. Valuation remains unavailable until an as-of-dated, legally reusable target is licensed or approved.

## Alternatives
Unofficial scraping, copied datasets, or invented proxy labels.

## Consequences
The valuation training contract can be built and tested, but no production estimate is emitted without legitimate targets.
