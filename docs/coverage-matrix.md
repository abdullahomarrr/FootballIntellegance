# Coverage matrix

**Observed:** 2026-09-29. `D` direct, `R` derivable, `U` unavailable, `P` paid/contract required, `?` not verifiable without authenticated discovery. A slash means sources differ. This matrix records evidence, not aspirations.

All 23 catalogued Big Five StatsBomb sample competition-seasons have immutable raw and
season-level reports (652 matches), and all four full 2015/16 seasons are materialized (1,517
matches). `D` describes verified source availability and, for those rows, completed warehouse
ingestion unless a row explicitly says partial sample.

## Capability interpretation

| Source code | Provider | Fixtures | Player metadata | Season stats | Match stats | xG | Advanced | Events | Coordinates | Transfers/fees/values | Injuries/contracts | Update |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| AF | API-Football | D* | D* | D* | D* | ? | D* | D (match incidents) | U | D / ? / ? | D / ? | live/current advertised |
| FD | football-data.org | D | D/P | U | limited P | U | limited P | limited D/P | U | U | U | live or delayed by plan |
| WO | Wyscout open | D | D | R | R | R | D | D | D | U | U | frozen |
| SB | StatsBomb open | D | D | R | R | D/R | D | D | D | U | U | irregular repository updates |

`AF` starred cells mean the endpoint is publicly advertised, but exact league-season depth is `?` until the authenticated `/leagues` coverage payload and sample endpoints are persisted. API-Football event data means fixture incidents, not spatial event logs.

## Big Five target seasons

Each row is explicit because coverage is a property of `(provider, competition, season, capability)`, never of the provider brand alone. `AF ?` means the candidate broad feed must be queried. Event enrichment reflects catalogued open data as of the audit.

| League | Season | Broad/live stats | Open event data | Coordinates | xG | Status / action |
|---|---|---|---|---|---|---|
| Premier League | 2015/16 | AF ?; FD P history | SB D (380) | SB D | SB D | full league match count; query AF |
| Premier League | 2016/17 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2017/18 | AF ?; FD P history | WO D | WO D | WO R | Wyscout complete season |
| Premier League | 2018/19 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2019/20 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2020/21 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2021/22 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2022/23 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2023/24 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2024/25 | AF ?; FD P history | U | U | U | query AF |
| Premier League | 2025/26 | AF ?; FD D/P | U | U | U | query AF |
| Premier League | 2026/27 | AF ?; FD D/P | U | U | U | live; mandatory validation |
| La Liga | 2015/16 | AF ?; FD P history | SB D (380) | SB D | SB D | full league match count; query AF |
| La Liga | 2016/17 | AF ?; FD P history | SB D (34) | SB D | SB D | partial sample; query AF |
| La Liga | 2017/18 | AF ?; FD P history | SB D (36) + WO D | D | SB D / WO R | WO is full season; SB is sample |
| La Liga | 2018/19 | AF ?; FD P history | SB D (34) | SB D | SB D | partial sample |
| La Liga | 2019/20 | AF ?; FD P history | SB D (33) | SB D | SB D | partial sample |
| La Liga | 2020/21 | AF ?; FD P history | SB D (35) | SB D | SB D | partial sample; selected 360 |
| La Liga | 2021/22 | AF ?; FD P history | U | U | U | query AF |
| La Liga | 2022/23 | AF ?; FD P history | U | U | U | query AF |
| La Liga | 2023/24 | AF ?; FD P history | U | U | U | query AF |
| La Liga | 2024/25 | AF ?; FD P history | U | U | U | query AF |
| La Liga | 2025/26 | AF ?; FD D/P | U | U | U | query AF |
| La Liga | 2026/27 | AF ?; FD D/P | U | U | U | live; mandatory validation |
| Bundesliga | 2015/16 | AF ?; FD P history | SB D (34) | SB D | SB D | partial sample |
| Bundesliga | 2016/17 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2017/18 | AF ?; FD P history | WO D | WO D | WO R | Wyscout complete season |
| Bundesliga | 2018/19 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2019/20 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2020/21 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2021/22 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2022/23 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2023/24 | AF ?; FD P history | SB D (34) | SB D | SB D | partial sample; selected 360 |
| Bundesliga | 2024/25 | AF ?; FD P history | U | U | U | query AF |
| Bundesliga | 2025/26 | AF ?; FD D/P | U | U | U | query AF |
| Bundesliga | 2026/27 | AF ?; FD D/P | U | U | U | live; mandatory validation |
| Serie A | 2015/16 | AF ?; FD P history | SB D (380) | SB D | SB D | full league match count |
| Serie A | 2016/17 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2017/18 | AF ?; FD P history | WO D | WO D | WO R | Wyscout complete season |
| Serie A | 2018/19 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2019/20 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2020/21 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2021/22 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2022/23 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2023/24 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2024/25 | AF ?; FD P history | U | U | U | query AF |
| Serie A | 2025/26 | AF ?; FD D/P | U | U | U | query AF |
| Serie A | 2026/27 | AF ?; FD D/P | U | U | U | live; mandatory validation |
| Ligue 1 | 2015/16 | AF ?; FD P history | SB D (377) | SB D | SB D | three short of 380; investigate |
| Ligue 1 | 2016/17 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2017/18 | AF ?; FD P history | WO D | WO D | WO R | Wyscout complete season |
| Ligue 1 | 2018/19 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2019/20 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2020/21 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2021/22 | AF ?; FD P history | SB D (26) | SB D | SB D | partial sample; selected 360 |
| Ligue 1 | 2022/23 | AF ?; FD P history | SB D (32) | SB D | SB D | partial sample; selected 360 |
| Ligue 1 | 2023/24 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2024/25 | AF ?; FD P history | U | U | U | query AF |
| Ligue 1 | 2025/26 | AF ?; FD D/P | U | U | U | query AF |
| Ligue 1 | 2026/27 | AF ?; FD D/P | U | U | U | live; mandatory validation |

## Remaining requested capabilities

For **every row above**, transfers, fees, values, injuries and contracts are currently:

- Transfers: `AF ?` until season samples are inspected.
- Fees: `?`; an endpoint name does not prove populated fees.
- Historical/current values: `U/?`; no approved market-value source.
- Injuries: `AF ?`; endpoint advertised, exact historical depth unproved.
- Contracts: `?`; no public evidence of complete historical contracts.
- Cost/plan: AF paid plan required for unrestricted historical discovery; FD history/deep fields paid; WO/SB open with attribution/license obligations.

These fields are deliberately not copied as five repetitive columns with false certainty.

## Machine-readable system of record

Open-provider discovery is materialized as checksum-linked
`provider_coverage_observation` records. This Markdown is a human-readable audit view; an
authenticated live-provider run must append its observed capability payloads rather than
turning unknown cells into assumptions.
