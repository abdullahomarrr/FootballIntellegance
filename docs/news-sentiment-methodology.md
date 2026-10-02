# News and sentiment methodology

## Bluesky public conversation

Bluesky observations come from the unauthenticated public AppView search endpoint. The
pipeline stores text and engagement metadata but deliberately excludes avatars, thumbnails
and embedded media. Exact posts are immutable and content-addressed; unchanged replays do
not create new observations. Daily player/topic aggregates expose mention count, mean score,
model version and as-of time.

The `football_lexicon_v1` score is a small, explainable English-language tone indicator. It
is not a football-performance measure, is not representative polling, and will under-read or
misread other languages, sarcasm and context. The product therefore labels it external
context only and never uses it in similarity, valuation, tactical fit or squad optimization.

## Current status

No news or social credentials and no approved commercial retention rights are available.
Production ingestion is therefore disabled and the corresponding player feeds are empty.
The frontend states this limitation rather than presenting sample stories or sentiment as
real observations.

## Implemented boundary

News records support canonical URLs, permitted snippets, publisher and publication time,
story clustering, topics, provenance, and conservative player linking. Deduplication prefers
canonical URL and then near-duplicate title evidence. Full publisher articles are not copied.

The local football lexicon scorer operates only on text the user is authorized to process.
It returns matched terms and a versioned label and is always marked
`EXTERNAL_CONTEXT_ONLY`. It does not infer ability, character, transfer probability, or
future performance.

## Approval requirements

Before activation, record the API plan, search history, rate limits, storage/redistribution
rights, deletion requirements, supported languages, and representative response samples.
Social data should be aggregated promptly to player/day/topic counts and mean sentiment;
raw personal content should not be retained by default. A labeled football-domain set is
required to measure precision, recall, F1, calibration, language bias, sarcasm failures, and
entity-link error. Until then, sentiment is a transparent baseline rather than a validated
NLP model.

