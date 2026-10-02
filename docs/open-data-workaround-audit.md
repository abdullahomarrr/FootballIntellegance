# Open-data workaround audit

Updated: 2026-09-30

This is the decision log for the credential-free data phase. A source being publicly
reachable does not automatically make every field or media asset safe to republish.

| Source | Verified access and status | Permitted role | Current implementation | Boundary |
|---|---|---|---|---|
| OpenFootball `football.json` | Public GitHub repository, CC0-1.0, 2026/27 directory present; latest-season JSON is generated daily from community-maintained Football.TXT upstream | Primary credential-free fixtures and results where a configured competition file exists | Adapter and canonical backfill are live for seven leagues: 2,364 fixtures, 353 finished and 2,011 scheduled as of 2026-09-29. Exact raw snapshots, source observations and provider bridges are persisted | Community data is not guaranteed complete or live; absence remains null/uncovered, never inferred |
| TheSportsDB | Official free v1 key `123`, 30 requests/minute; free endpoints are restricted | Secondary cross-check and gap evidence using documented endpoints | Daily ingestion is live and immutable/raw-backed. The 2026-09-29 run stored three U21 events; replay inserted zero duplicates. Exact date/home/away matching is required before attaching it to a canonical match, and conflicts are preserved instead of overwriting | Not primary truth. No artwork is ingested: license/trademark/third-party rights must be verified per asset. Published app-store use requires paid subscription |
| GDELT DOC 2.0 | Public full-text news search, JSON output | Article discovery and metadata only | `GDELTAdapter.search_articles` emits URL/title/date with no copied article body or synthetic snippet. A fresh five-record, one-week query on 2026-09-30 again returned HTTP 429 from the shared network | Publisher rights still apply; the platform links to the canonical publisher and does not mirror content. Live ingestion remains unavailable until the public service accepts this host |
| Bluesky public AppView | Official docs permit unauthenticated `app.bsky.*` GETs. The documented `public.api.bsky.app` hostname returned a CDN 403 from this host, while Bluesky's public `api.bsky.app` AppView returned the same endpoint without authentication | Public-post discovery and aggregate sentiment inputs | Live ingestion is working through the public Bluesky AppView. A 100-post Kylian Mbappe query produced two daily aggregates; exact posts are immutable/raw-backed and unchanged replay inserted zero duplicates. Artwork and embeds are not ingested | Public conversation is noisy and non-representative. UI labels it context-only and exposes sample size and lexicon model version |
| `dcaribou/transfermarkt-datasets` | Repository labels its prepared dataset CC0; publisher warns updates are paused and data stops in June/July 2026; CC0 text disclaims clearing third-party rights | Candidate historical research snapshot only, subject to a recorded legal/product decision | Not ingested yet | Never scrape Transfermarkt. Do not describe this frozen snapshot as current. Repository licensing cannot warrant rights it does not own |

## Source precedence

1. A provider's official, explicitly permitted record for its own competition.
2. OpenFootball for configured fixture/result coverage.
3. TheSportsDB as corroborating evidence only.
4. Derived metrics, always linked to input provider(s), model version, and as-of time.

Conflicts are retained as separate observations. A lower-precedence source never silently
overwrites a higher-precedence value. Unknown, unavailable, and not-covered are distinct
from zero.

## Initial repository audit

Before this phase the warehouse already had canonical match, transfer, valuation, news and
social aggregate tables, raw immutable storage, pipeline-run tracking, provider bridges, and
coverage-aware API concepts. It had no credential-free adapters for OpenFootball,
TheSportsDB, GDELT or Bluesky and no trained valuation model. The web application exposed
many endpoint payloads as raw JSON and required internal numeric IDs or pasted JSON in core
workflows. Those are open acceptance failures, not cosmetic follow-ups.

## External or optional follow-up

- Add cross-provider conflict detection against corroborating sources; OpenFootball canonical
  persistence and unchanged-source replay idempotency are complete and tested.
- Extend TheSportsDB corroboration on days containing configured club competitions; the
  free daily endpoint, immutable storage, exact-only linking and replay idempotency are tested.
- Record a defensible decision on the historical market dataset before ingestion; if used,
  label it historical/frozen everywhere.
- Persist GDELT articles when the public host permits this environment. Bluesky raw posts,
  daily aggregates, replay idempotency, sample sizes and context-only UI are complete.
- Train and temporally evaluate valuation only after enough lawful historical targets exist.
- Extend the current browser regression checks if the product gains additional routes or
  providers; all current routes and core journeys have been validated locally.
