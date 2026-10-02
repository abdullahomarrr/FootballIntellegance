# Local development

## Prerequisites

Install Docker Desktop, Node.js, and `uv`. Copy `.env.example` only when credentials are
available; never commit secrets. The default PostgreSQL password is for local development.

## Start services

```powershell
docker compose up -d postgres
uv sync
uv run python -m football_intelligence.cli --help
uv run dbt build --profiles-dir .
npm --prefix apps/web ci
npm --prefix apps/web run build
docker compose up --build api web
```

The API defaults to `http://localhost:18000` in Compose and the web application to
`http://localhost:13000`. Outside Compose, set `DATABASE_URL` and
`NEXT_PUBLIC_API_URL` explicitly.

## Verification

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run dbt build --profiles-dir .
npm --prefix apps/web run build
docker compose config --quiet
```

Real-data commands are documented by `--help`. Backfills require explicit provider
competition/season IDs and checkpoint/report paths. A checkpoint is written after each
match; rerunning the same command skips completed IDs. Raw files under `data/raw` are
content-addressed and ignored by Git. Reports under `data/reports` contain evidence but no
credentials.

Do not enable API-Football, news, social, or valuation jobs until the required key, plan,
terms, and retention review are recorded.
