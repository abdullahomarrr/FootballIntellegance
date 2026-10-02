# Football lexicon sentiment v1

## Purpose

Provide a deterministic, locally testable baseline for aggregate public-context pipelines without calling or scraping an external platform.

## Method and evaluation

A small versioned football-oriented polarity lexicon with immediate preceding negation. It emits score, label and matched terms. Before production it requires a manually labeled, source-representative football corpus evaluated for macro F1, per-class precision/recall, calibration, sarcasm, multilingual text and drift.

## Limitations

This is not production NLP. It misses context, irony, entities and most football vocabulary. It must only appear as external market context, never as player quality or a recruitment objective. External ingestion remains blocked until API, retention and derived-use rights are approved.
