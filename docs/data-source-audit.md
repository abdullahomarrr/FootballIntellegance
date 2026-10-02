# Data-source audit

**Audit date:** 2026-09-28  
**Scope:** Big Five leagues, 2015/16–2026/27, with live 2026/27 support and supplemental event, market, news, and social data.

## Executive decision

There is no verified, lawful, affordable single source for the complete product. Use a provider-independent architecture and three source classes:

1. **Broad/live operational feed:** run a time-boxed API-Football paid-plan validation. Its public material confirms all plans expose fixtures, player statistics, transfers, sidelined/injuries and related endpoints, but its detailed coverage explicitly varies by season and fixture. Public documentation does **not** prove the required Big Five player-stat depth for every target season. Procurement is gated on an authenticated discovery export.
2. **Open event enrichment:** ingest the Wyscout research release for the complete 2017/18 Big Five season and StatsBomb Open Data for the selected seasons actually listed in `competitions.json`. Neither is a live longitudinal backbone.
3. **Live fixture fallback/control:** football-data.org covers all Big Five leagues and is useful for fixture/result reconciliation, but it is not sufficient for player recruitment profiles: its published packages focus on fixtures, tables, lineups, scorers, bookings and squads rather than broad player performance facts.

Market values, contracts, news, and social sentiment remain separate procurement tracks. Do not scrape Transfermarkt or social sites.

## Repository inspection

The existing repository contains a Python/FastAPI backend, Next.js frontend, PostgreSQL
migrations, dbt models, provider adapters, immutable raw store, analytical/model baselines,
Docker Compose, CI, tests and documentation. The implementation audit is maintained in
`current-system-audit.md`; this source audit does not infer capabilities from filenames.

## Broad football providers

### API-Football — preferred validation candidate, not yet approved

Publicly verified:

- Coverage page reports 1,244 competitions and says detailed capabilities may vary by season or fixture.
- Coverage page was last updated 2026-09-11 when checked.
- All published plans list leagues, fixtures, events, lineups, statistics, players, transfers, sidelined and injuries.
- Free plan: 100 requests/day and limited seasons.
- Pro: USD 19/month and 7,500 requests/day; Ultra: USD 29/month and 75,000/day; Mega: USD 39/month and 150,000/day at audit time.
- The leagues endpoint is the authoritative machine-readable coverage discovery mechanism according to the provider terms.

Not publicly proven without credentials:

- exact Big Five seasons returned by the subscribed plan;
- whether player season statistics and fixture-player statistics are complete for every season;
- per-season availability of xG and advanced fields;
- transfer fee, market value and contract completeness;
- historical corrections and redistribution rights.

Decision: buy at most one month of Pro for discovery after accepting terms; do not bulk ingest until the discovery artifact and a sample reconciliation pass.

Sources: [coverage](https://www.api-football.com/coverage/), [pricing](https://www.api-football.com/pricing), [terms](https://www.api-football.com/terms), [documentation](https://www.api-football.com/documentation-v3).

### football-data.org — control/fallback for fixtures

Publicly verified:

- The free competition set includes Premier League, Bundesliga, Ligue 1, Serie A and La Liga.
- Free tier provides delayed scores, fixtures/schedules and tables at 10 calls/minute.
- “Free + Deep Data” adds lineups/substitutions, scorers, cards and squads for EUR 29/month.
- “ML Pack Light” advertises ten seasons of history for EUR 29/month.
- A statistics add-on covers team/match measures such as shots, possession and fouls, not the player-season analytical breadth required here.

Decision: suitable as an independent fixture/result reconciliation source or low-cost live schedule source; unsuitable as the sole player intelligence source.

Sources: [coverage](https://www.football-data.org/coverage), [pricing](https://www.football-data.org/pricing), [API quickstart](https://www.football-data.org/documentation/quickstart).

### Commercial scouting/event vendors

StatsBomb commercial, Hudl Wyscout and Opta/Stats Perform are credible future adapters. Public list pricing and exact redistribution rights are not available in a form sufficient for this portfolio audit. Treat all production use as **PAID / CONTRACT REQUIRED**, not as an implied future entitlement.

## Open event datasets

### Wyscout Soccer Match Event Dataset

Verified through the Figshare collection and accompanying Scientific Data paper:

- all matches from one full season of Premier League, La Liga, Bundesliga, Serie A and Ligue 1 (2017/18);
- FIFA World Cup 2018 and UEFA Euro 2016;
- events include pass, duel, free kick, foul, shot, save attempt, goalkeeper leaving line, offside, interruption and other/sub-events;
- event keys include event/sub-event identifiers, tags, event seconds, match period, player ID, match ID, team ID, and one or two positions;
- coordinates are percentage-like `(x, y)` positions on a 0–100 reference frame; orientation must be normalized while preserving raw positions;
- separate players, teams, competitions, matches, coaches, referees and identifier dictionaries exist.

Limitations:

- one Big Five season only;
- no live updates;
- no native xG/xA field (derivable models may be built later and must be labeled as project-derived);
- player IDs are Wyscout-specific;
- the inspected Figshare dataset items declare **CC BY 4.0**; preserve creator/source attribution and record the license URL with every raw manifest.

Sources: [Figshare collection](https://figshare.com/collections/Soccer_match_event_dataset/4415000), [data paper](https://www.nature.com/articles/s41597-019-0247-7).

### StatsBomb Open Data

The repository provides JSON competition/season catalogues, matches, events, lineups and selected 360 frames. Inspection of `competitions.json` on 2026-09-27 found these Big Five entries:

| League | Seasons present |
|---|---|
| Premier League | 2003/04 (38 matches), 2015/16 (380) |
| La Liga | 1973/74 (1), 2004/05–2014/15 (7–38 per season), 2015/16 (380), 2016/17–2020/21 (33–36 per season) |
| Bundesliga | 2015/16 (34), 2023/24 (34) |
| Serie A | 1986/87 (1), 2015/16 (380) |
| Ligue 1 | 2015/16 (377), 2021/22 (26), 2022/23 (32) |

The match counts above were read directly from each catalogued match JSON file. They prove that most catalogue entries are samples, not full seasons: among target years, only Premier League, La Liga and Serie A 2015/16 contain 380 matches; Ligue 1 2015/16 has 377; the other listed target seasons contain 26–36 matches. Event JSON supports rich action types and locations; shots may carry StatsBomb xG. Selected matches—not all—have 360 data. StatsBomb requires attribution when publishing analysis.

Sources: [official repository](https://github.com/statsbomb/open-data), [live competition catalogue](https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json).

## Market and transfer data

| Option | Historical depth | Freshness | Fields | Suitability | Decision |
|---|---|---|---|---|---|
| API-Football transfers | Authenticated discovery required | advertised live/current | transfers endpoint; fee/value/contract completeness unproven | candidate for transaction context only | validate samples |
| Transfermarkt website/unofficial endpoints | broad in site UI | current | fees, values, contracts | automation/redistribution rights not established | **do not scrape** |
| Kaggle/community exports | varies | usually stale | varies | provenance and redistribution often unclear | fixtures/tests only if license is explicit |
| Commercial scouting vendors | likely strong | current | vendor-specific | contract and cost required | future procurement |

No current source is approved for authoritative historical market-value time series. Phase 1 should store completed transfer records only where returned under an accepted provider agreement. The valuation-model phase is blocked until an as-of-dated, legally reusable target series is procured.

## News options

### NewsAPI.org

- Developer plan: free, 100 requests/day, 24-hour delay, one-month lookback, development/testing only.
- Business: USD 449/month, real-time, five-year search, 250,000 requests/month at audit time.
- Results do not include full article content. The provider suggests URLs, but that does not grant permission to scrape publishers.

Decision: useful for a local proof of ingestion and article metadata only; not approved for a deployed product on the free plan. Store metadata and permitted snippets, not copied articles.

Source: [NewsAPI pricing](https://newsapi.org/pricing).

Event Registry / NewsAPI.ai advertises archive access since 2014 and paid plans starting at USD 90/month, with a limited free search allocation. Terms and retention rights require a separate review before adoption. Source: [plans](https://newsapi.ai/plans).

## Social options

### Reddit

Official Data API access requires registration and compliance with changing limits. The 2026 terms require a separate agreement for commercial use, excess research use, or use outside expressly permitted cases; bulk export is significantly limited. User-content retention/deletion obligations make permanent raw mirroring risky.

Decision: no Phase 1 dependency. Later prototype only after approval, minimize stored personal data, aggregate quickly, retain source IDs rather than indefinite text, and implement deletion handling.

Sources: [Data API terms](https://redditinc.com/policies/data-api-terms), [developer access guidance](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data).

### X and other networks

No source was approved in this audit. API tiers, search history, storage, derived-data, and redistribution terms need contract review. Do not substitute scraping.

## Coverage discovery contract

Every adapter must implement:

```python
class ProviderAdapter(Protocol):
    def discover_coverage(self, checked_at: datetime) -> list[CoverageObservation]: ...
    def fetch(self, request: ProviderRequest) -> RawObject: ...
    def normalize(self, raw: RawObject) -> Iterable[CanonicalRecord]: ...
```

Discovery writes immutable observations with the request parameters, response checksum, plan name, and terms version. A current view may be built from the latest successful observation; the history is never overwritten.

## Approval gates

Before the broad provider is approved, the authenticated discovery run must prove:

1. League and season identifiers for every Big Five target season.
2. Per-season feature flags returned by the provider—not marketing-page inference.
3. Ten fixture samples per league across old, recent, and live seasons.
4. Player-season and player-match reconciliation for at least two teams per sampled season.
5. Pagination, rate-limit, retry, correction and deletion behavior.
6. Written terms covering local persistence, derived analytics, screenshots/demo and public deployment.
7. Cost projection for historical backfill plus weekly live refresh.

Failure of any gate changes the first milestone scope; it must not be hidden with mock data.
