<p align="center">
  <img src="docs/images/banner.webp" alt="Football Intelligence" width="100%">
</p>

<h3 align="center">A football recruitment platform that turns raw match data into scouting decisions you can defend</h3>

<p align="center">
  Deep player breakdowns, every top-five-league squad with alternatives and upgrades,<br>
  role-based player search and evidence-backed shortlists. No mystery ratings:<br>
  every number shows where it came from.
</p>

<p align="center">
  <a href="https://footballintelligencesystem.vercel.app"><b>Live site →</b></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-FastAPI-3776AB">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-000000">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-336791">
  <img alt="dbt" src="https://img.shields.io/badge/dbt-warehouse-FF694B">
  <img alt="CI" src="https://img.shields.io/badge/CI-ruff%20%7C%20mypy%20%7C%20pytest-2ea44f">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

## What it does

**Player breakdowns.** Every player gets a full scouting file: a playing-style archetype with a
secondary profile, strengths with the evidence behind each one, the questions a scout should
still answer, tactical fit with their team, role-fit scores, 15 advanced stats ranked against the
same position, heatmaps by action type, an expected-threat zone map, pass and shot maps,
season-by-season development, similar players, market value history and a written scouting
report you can copy in one click.

**Club squads.** All 96 top-five-league clubs, each shown as a likely starting XI on a pitch.
Click a player for current-season stats, heat map, shot map, market value and injury status.
The tool searches all five leagues for players in the same role, flags upgrades who are better at
exactly what that player does best, and lines any of them up side by side, stat by stat.

**Recruitment search.** Pick a player you rate and one of 16 roles (deep-lying playmaker,
pressing forward, ball-playing centre-back, sweeper goalkeeper…). It ranks the closest matches,
explains each one, and can filter by market value.

**Shortlists.** Candidates keep their ranking, workflow stage and the evidence for why they're
there, with a squad coverage and budget view.

**Press & media.** Latest news and fan conversation for any player, with every claim quoted from
its source, dated and labelled unverified, and kept apart from football performance.

## How the intelligence works

Everything below is plain arithmetic on real data, so every score can be traced back to the
numbers that produced it.

### Percentiles

Each stat is computed per 90 minutes from match events, then ranked against players in the same
broad position (goalkeeper, defender, midfielder, forward) with at least **900 minutes**. Players
are ranked within their own competition-season when that group has 15 or more players;
otherwise they are ranked in a wider pool of the same position from the same data provider, and
the page says so. Stats where lower is better (turnovers, goals conceded) are flipped, so a high
percentile always means "better".

### Expected threat (xT)

The pitch is split into a 12 × 8 grid. Each zone gets a value that rises steeply as it gets
closer to goal and is higher through the middle:

```
zone value = (distance up the pitch)³ × (0.65 + 0.35 × closeness to the centre)
```

Every completed pass or carry earns the value of where it ends minus where it started, so a ball
moved from midfield into the box scores far more than one moved sideways. A player's xT added is
the sum per 90. It is a transparent, versioned baseline rather than a black-box model.

### Archetypes

Each position has its own catalogue of playing styles (for forwards: penalty-area goal threat,
dribbling ball-carrier, link-up forward, pressing forward, creative attacker…). Every style is a
weighted recipe of stats. A player's score for a style is the **weighted average of their
percentiles** on those stats.

- **Primary** is the highest-scoring style. A **secondary** style is shown if it also scores 65+.
- **Clarity** says how much to trust the label:
  - **Clear**: the primary wins by 5+ points.
  - **Blended**: the top two are within 5 points, so the player is a hybrid.
  - **Weak**: nothing reaches the 55th percentile on average.
  - **Limited**: some styles couldn't be scored because the data provider doesn't record a stat
    they need.
- A style is only scored if at least two of its stats, and half of its weight, are available.

### Similar players (historical data)

Two players are compared on every advanced stat they share, in the same league, season and
position:

```
similarity = 100 − average gap between their percentiles
```

A pair needs at least three shared stats and 60% overlap with the reference player's stats, so
thin evidence never produces a confident-looking match. Each result shows the closest stat, the
biggest difference and a confidence level.

### Role fit and recruitment ranking

A role is a set of stat weights (for a deep-lying playmaker: pass completion, passing under
pressure and progressive passes count most). **Role fit** is the weighted average of a player's
percentiles using those weights. When you search with a role, results are ranked by:

```
overall match = 60% style similarity + 40% role fit
```

The two scores stay visible separately, so you can see whether a player is there because they
play like your reference, because they suit the role, or both.

### Tactical context

A team's style is the minutes-weighted average of its players' percentiles on four axes: keeping
the ball, progressing it, pressing and winning it, and creating chances. The strongest axis names
the style (for example "Possession-secure"). The page then shows where a player is **10+ points
above** the team (what they add) and **10+ points below** (where the squad carries them).

### Squad alternatives and upgrades (current season)

Current-season players are compared only within their role family (keepers, full-backs,
centre-backs, midfielders, wingers, strikers). Every per-90 stat is re-ranked across all cached
players in that family, so numbers are comparable across leagues. Players need 180+ minutes and
at least 10 shared stats.

- **Similar players** use the same formula as above: 100 minus the average percentile gap.
- **Upgrades** must be at least 60% similar and score higher overall, but the comparison counts
  each stat more where the clicked player is strong:

  ```
  stat weight = 0.25 + 0.75 × how far above average the clicked player is on that stat
  ```

  So a winger's upgrade is judged mainly on chances and dribbles, not on clearances. Discipline
  and team-dependent stats are excluded, noisy low-volume percentages are dropped, and gaps that
  only exist because both numbers are near zero are hidden.

The likely starting XI is estimated from minutes played this season and each player's listed
positions. It shows who has played most, not an official team sheet.

### Scouting reports and news

The written report is generated from the same evidence on the page: archetype, strengths,
questions, tactical context and role fit. News claims are extracted by an LLM, and a grounding
check drops any claim whose quote doesn't appear word for word in the source.

## Design decisions worth knowing

- **Provider data is never merged.** StatsBomb and Wyscout records stay separate, and a *person*
  layer groups them for display so nothing is double-counted.
- **Ambiguity is dropped, not guessed.** Identity links use full names or shared IDs, and
  conflicting claims are discarded.
- **No invented data.** Missing coverage shows as missing, never as zero or a mock record.
- **Limits are part of the product.** Coverage notes, sample warnings and "what this can't say"
  sections sit next to the results.
- **Removed on purpose.** A performance-versus-value model was built, found to rest on cohorts too
  thin to trust, and cut.

## Data and honest limits

- **Event data:** 11.7 million events from open StatsBomb and Wyscout data, mostly the 2015/16 and
  2017/18 seasons, plus the 2022 World Cup, Euro 2020 and 2024, Copa América 2024 and AFCON 2023.
  Recent full club seasons are not openly released.
- **Current season:** squads, per-90 stats, heat maps and shot maps for all 96 top-five-league
  clubs come from FotMob's public pages, for personal, non-commercial use (see
  [the source notes](docs/data_sources/fotmob-pages.md)). Premier League and La Liga stats tiers
  come from free public feeds and have no event locations.
- **Market data** is a frozen, licence-checked snapshot, not live.
- Wyscout doesn't record pressures, recoveries or carries, so some stats don't exist for its
  players.
- See [known limitations](docs/known-limitations.md) and the
  [intelligence validation](docs/intelligence-validation.md) record.

## Hosting on a $0 stack

| Part | Where |
| --- | --- |
| Web app (Next.js) | Vercel, free tier |
| API (FastAPI, Docker) | Render, free tier, from [`render.yaml`](render.yaml) |
| Database (PostgreSQL) | Neon, free tier |

The local database is about 7 GB, almost all of it one table of raw match events. The hosted
copy is about 200 MB: every player-season's heatmaps, pass maps, shot maps and threat zones are
precomputed into a small snapshot table (`build-spatial-snapshot`), and the API serves those
with `SPATIAL_SNAPSHOT=1`. The maps are identical to the live computation.

Render's free tier sleeps when idle, so a [scheduled GitHub Action](.github/workflows/keep-api-awake.yml)
pings the API every 10 minutes, and the web app shows a loading screen while it wakes.

---

# Technical reference

- [Data-source audit](docs/data-source-audit.md)
- [Coverage matrix](docs/coverage-matrix.md)
- [Canonical data model](docs/data-model.md)
- [Architecture](docs/architecture.md)
- [Player intelligence methodology](docs/player-intelligence-methodology.md)
- [Similarity methodology](docs/similarity-methodology.md)
- [Risk register](docs/risk-register.md)
- [Real-data validation report](docs/data-validation-report.md)
- [Performance validation](docs/performance-validation.md)
- [Intelligence validation](docs/intelligence-validation.md)
- [Final status register](docs/final-status.md)

## Local development

```bash
uv sync --all-groups
uv run ruff check .
uv run mypy
uv run pytest
docker compose up -d --wait
uv run dbt build --profiles-dir .

# API
uv run uvicorn football_intelligence.api:app --port 8000

# Web, in another terminal
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npx next dev -p 13000

# Precompute pitch maps for a hosted database
uv run python -m football_intelligence.cli build-spatial-snapshot
```

Copy `.env.example` to `.env` before using non-default local credentials. Never commit provider
keys.

<details>
<summary><b>Build log: everything implemented</b></summary>

- Immutable, checksum-verified local raw object store
- Typed coverage and raw-manifest contracts
- StatsBomb Open Data Big Five discovery with real match counts
- Wyscout/StatsBomb coordinate normalisation to 105 × 68 metres
- PostgreSQL coverage, identity, bridge, match and canonical event schema
- Conservative cross-provider player identity scoring and review path
- StatsBomb and Wyscout canonical event normalisation
- Coverage-aware per-90, percentile, sample-confidence and similarity analytics
- Explainable recruitment ranking with age, budget and minute constraints
- dbt player-season marts with warehouse data tests
- Event quality quarantine rules and a versioned xT baseline
- Resumable multi-match season backfills with atomic checkpoints
- News URL deduplication, conservative player linking, topics and claim provenance
- Evidence-backed scouting reports
- Complete Wyscout Open 2017/18 Big Five load: 1,826 matches, 3,071,392 events and 50,584
  player-match rows
- StatsBomb Open expansion across 23 Big Five catalogue seasons, and complete 2015/16 loads for
  La Liga, Ligue 1, Premier League and Serie A
- StatsBomb Open tournament event data (World Cup 2022, Euro 2020/2024, Copa América 2024,
  AFCON 2023)
- Current-season stats tiers for the Premier League (public FPL feed) and La Liga (free Big Ball
  Sports API tier)
- Club squads for all 96 top-five-league clubs with a likely XI, player photos and an
  alternatives and upgrades finder
- Current-season head-to-head comparisons
- Position-specific and goalkeeper metrics, archetypes with secondary profiles, team tactical
  context, role fit, archetype discovery and a copyable scouting brief
- 16 built-in recruitment roles across every position
- Heatmap layers, xT zone map, pass and distribution maps and a filterable shot map
- Persistent recruitment roles and shortlists with ranking, workflow stage, rationale, budget
  view and archive support
- Source-linked news and fan-conversation research with quoted, dated, unverified claims
- Precomputed spatial snapshot for free-tier hosting, configurable CORS, keep-awake ping and a
  wake-up loading screen
- Ruff, mypy, pytest with coverage, and GitHub Actions CI

</details>

## License

[MIT](LICENSE) © 2026 Abdullah Omar
