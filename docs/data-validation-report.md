# Real-data validation report

Validation date: 2026-09-30

## Loaded Wyscout Open scope

The permitted public dataset contains the complete 2017/18 top divisions for England,
France, Germany, Italy, and Spain. The canonical database currently contains 1,826 matches,
3,071,392 accepted Wyscout events, and 50,584 player-match rows covering 2,567 players.
Three malformed coordinate events were quarantined rather than clipped or silently loaded.

The player-match loader observed 50,590 participants. Six could not be linked to a canonical
player and were excluded with an explicit unresolved count in the country reports. The five
reports are under `data/reports/wyscout-player-match-*.json`.

## Warehouse results

The final `dbt build --profiles-dir .` produced:

- 12,219 player-team-competition-season profiles;
- 3,287 profiles meeting the 900-minute comparison threshold;
- four broad position populations;
- 26,296 percentile rows across eight metrics; and
- 110,962 provider-player-match event profiles.

All 20 dbt model and data tests passed. Percentiles span 0 to 100 for every published metric.
Low-minute player-seasons remain in the profile mart with explicit sample confidence, but
are excluded from the comparison mart.

## Idempotency and failure behavior

Replaying England left the database unchanged at 3,071,392 events, 1,826 matches, and 2,568
provider players. Evidence is recorded in `data/reports/wyscout-idempotency.json`. Invalid
coordinates enter `data_quarantine` with the raw payload and reason. A real archive schema
variant where substitutions is the string `"null"` is now handled without fabricating
participation minutes, with a regression test.

## Application validation

The real similarity query was exercised on a qualified canonical midfielder and returned
named same-league/same-season/same-position peers with all eight feature differences. The
recruitment page now calls that endpoint; it contains no embedded fictional candidates.
The squad page no longer submits synthetic players, prices, or fit values, and explicitly
shows the licensed-input gate. The market page only scores text supplied by the user and no
longer embeds a sample sentiment claim.

Python formatting, lint, static typing, all tests, and the 80% coverage gate pass. The Next.js
production build also passes. This report does not claim current 2026/27 coverage, licensed
market observations, trained valuation metrics, real news, or public social data; those are
external access or licensing gates.

## StatsBomb Open expansion

The public StatsBomb catalogue was ingested for every Big Five competition-season with
fewer than 100 catalogued matches: 23 competition-seasons and 652 matches. The resumable
season reports record 18,408 player-match rows and zero unresolved event participants.
Lineup position intervals, rather than a fixed appearance assumption, determine minutes.
Goals, assists, shots, shots on target, passes, key passes, tackles and interceptions are
derived from native event attributes and remain provider-attributed.

Four complete 2015/16 catalogue seasons were also loaded: Premier League (380), La Liga
(380), Serie A (380) and Ligue 1 (377), adding 1,517 matches and 42,096 player-match rows.
Every full-season player-match report records zero unresolved participants.

During the catalogue load, 1,511 events had coordinates just outside the documented pitch
plane (typically 120.1–120.9 or 80.1–80.9). The normalizer now preserves those events and
their raw coordinates, leaves normalized coordinates null, and records explicit validation
errors. All 652 previously loaded sample matches were replayed under that corrected behavior
before the final dbt build. The canonical database now contains 3,995 matches and 10,846,880
events.

## Current verification boundary

The final repository verification passed 159 Python tests with 82.28% coverage, Ruff, strict
mypy and a Next.js production build covering all ten routes. The expanded warehouse passed
all 20 dbt nodes/tests. Database totals come from
`final-evidence-after-full-ingest.json`, not extrapolation from report files.

Failure-path tests now explicitly simulate a provider timeout followed by a successful
checkpoint retry, HTTP 429 rate limiting, malformed provider JSON, a missing API request
field, a database exception and an unknown canonical player. Failed ingestion is not marked
complete, rate limits and malformed responses are not converted to empty coverage, request
validation returns 422, unknown identity returns 404, and unexpected server failures return
a stable 500 JSON envelope without exposing database details or fabricated data.

## Cross-source sanity check

La Liga 2017/18 supplies a genuine overlap: StatsBomb catalogues 36 matches and Wyscout
contains the complete 380-match season. A deterministic comparison matched all 36 StatsBomb
matches to Wyscout using calendar date plus ordered normalized home and away clubs. All 36
matched on date, clubs and final score; no disagreement was suppressed or assigned to an
arbitrarily "authoritative" provider.

The comparison implementation is `cross_source.py` and has regression coverage for provider
name affixes, literal Unicode escape sequences in the Wyscout source, replacement-character
mojibake in the current StatsBomb catalogue, non-overlap and preserved score disagreement.
The name repair is an explicit small mapping, not fuzzy matching. Player identity remains
conservative where StatsBomb omits DOB; weak name-only cross-provider candidates are
deliberately not merged.

## Browser and responsive validation

The optimized Next.js build was served locally and exercised in a real browser across the
home, players, analysis, market, recruitment, shortlists, squad and coverage routes. Each
route rendered its expected primary heading. With PostgreSQL/API unavailable, database-backed
routes displayed explicit unavailable states rather than stale or invented observations.

The first narrow-viewport pass exposed horizontal overflow from the workflow minimum width
and the unbroken `LICENSED_TARGET_REQUIRED` token. CSS corrections were applied and the same
eight routes were re-measured at the mobile breakpoint; every route then had document
`scrollWidth == clientWidth`. The analysis route was also corrected to remove hardcoded
trait/minute/development payloads; it now compares two searched canonical players using their
real qualified profiles. The restored live stack subsequently passed player discovery, profile,
metric, spatial, similarity and evidence endpoints plus persistent role/shortlist creation,
addition, retrieval, stage changes and archival.

Populated player list, season, metric, spatial, market, news, sentiment and similarity
responses now expose source freshness and sample size where applicable. Season responses
also enumerate observed season statuses. Request-time `generated_at` remains separate from
source `data_as_of`, preventing a fresh API response from implying fresh underlying data.

CPU-only API performance was measured over 200 successful requests per operation. Median
latency was 2.463–2.584 ms and p95 was 3.484–5.233 ms for tactical fit, development,
in-memory comparison and a two-position exact optimization. Live database endpoint medians
were 22.33–48.74 ms for the measured core paths. A measured spatial scan was fixed with
migration 012, reducing its median from 481.80 ms to 22.62 ms and yielding an index-only
1.825 ms database plan. Details are in `performance-validation.md`.
