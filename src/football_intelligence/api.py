from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from football_intelligence import __version__
from football_intelligence.comparison import compare_profiles
from football_intelligence.current_season_routes import router as current_season_router
from football_intelligence.development import (
    DatedMetric,
    MetricDevelopmentObservation,
    development_trend,
    metric_development_trends,
)
from football_intelligence.discovery import archetype_catalogue, cached_index, discover
from football_intelligence.env import load_env_file
from football_intelligence.fpl_routes import router as fpl_router
from football_intelligence.laliga_routes import router as laliga_router
from football_intelligence.news import extract_topics
from football_intelligence.optimization import SquadCandidate, optimize_squad
from football_intelligence.providers.google_news_rss import GoogleNewsRSSAdapter
from football_intelligence.recruitment import Candidate, RecruitmentConstraints, rank_candidates
from football_intelligence.repository import (
    archetype_pool,
    archive_shortlist,
    coverage_by_season,
    coverage_observations,
    create_recruitment_role,
    create_shortlist,
    match_summary,
    openfootball_coverage,
    person_members,
    player_detail,
    player_intelligence,
    player_market,
    player_metrics,
    player_news,
    player_seasons,
    player_sentiment,
    player_spatial,
    players,
    provider_player_match_profile,
    recruitment_roles,
    remove_shortlist_player,
    shortlist_detail,
    shortlists,
    similar_players,
    team_context_rows,
    upsert_shortlist_player,
    values_at_seasons,
)
from football_intelligence.research import research_player
from football_intelligence.scout_report import build_scout_report, complete_metric_family
from football_intelligence.search_language import parse_scout_query
from football_intelligence.sentiment import score_text
from football_intelligence.squad_routes import router as squad_router
from football_intelligence.tactical import (
    build_tactical_context,
    classify_archetype,
    role_fit,
    tactical_fit,
)
from football_intelligence.valuation import valuation_availability

load_env_file()

Context = tuple[int | None, int | None, int | None]


def _context(
    team_id: int | None, competition_id: int | None, season_id: int | None
) -> Context | None:
    """An optional club-season chosen on the profile; None means the best-sampled one."""
    if team_id is None and competition_id is None and season_id is None:
        return None
    return (team_id, competition_id, season_id)


def _with_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the snapshot market value at the end of each row's season, when one is linked."""
    found = values_at_seasons(
        [
            (int(row["player_id"]), str(row["season_label"]))
            for row in rows
            if row.get("season_label")
        ]
    )
    for row in rows:
        hit = found.get((int(row["player_id"]), str(row.get("season_label"))))
        row["market_value_eur"] = float(hit["amount"]) if hit else None
        row["market_value_date"] = hit["valuation_date"] if hit else None
    return rows


def _pick_context(rows: list[dict[str, Any]], context: Context | None) -> dict[str, Any]:
    pool = rows
    if context is not None:
        keys = ("team_id", "competition_id", "season_id")
        matched = [
            row
            for row in rows
            if all(w is None or row.get(k) == w for k, w in zip(keys, context, strict=True))
        ]
        pool = matched or rows
    return max(
        pool, key=lambda row: (int(row.get("minutes_played") or 0), int(row.get("season_id") or 0))
    )

app = FastAPI(
    title="Football Recruitment Intelligence API",
    version=__version__,
    description=(
        "Coverage-aware recruitment intelligence. Unknown data is never represented as zero."
    ),
)
app.include_router(fpl_router)
app.include_router(laliga_router)
app.include_router(squad_router)
app.include_router(current_season_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:13000",
        *filter(None, (o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(","))),
    ],
    allow_origin_regex=os.environ.get("ALLOWED_ORIGIN_REGEX") or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


def _latest_value(rows: list[dict[str, Any]], key: str) -> Any | None:
    values = [row[key] for row in rows if row.get(key) is not None]
    return max(values) if values else None


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
    """Return a stable error envelope without leaking credentials or database details."""
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/meta")
def metadata() -> dict[str, object]:
    return {
        "generated_at": datetime.now(UTC),
        "feature_set_version": "foundation_v1",
        "providers": ["statsbomb_open", "wyscout_open"],
        "live_provider_status": "CREDENTIAL_REQUIRED",
    }


class CandidateRequest(BaseModel):
    player_id: int
    name: str
    age: int | None = None
    estimated_value: float | None = None
    minutes: int = Field(ge=0)
    features: dict[str, float | None]


class RecruitmentRequest(BaseModel):
    target_features: dict[str, float | None]
    candidates: list[CandidateRequest]
    maximum_age: int | None = None
    maximum_value: float | None = None
    minimum_minutes: int = Field(default=900, ge=0)
    feature_weights: dict[str, float] | None = None


class SquadCandidateRequest(BaseModel):
    player_id: int
    name: str
    positions: list[str]
    cost: float = Field(ge=0)
    fit_score: float


class SquadOptimizationRequest(BaseModel):
    needs: list[str]
    candidates: list[SquadCandidateRequest]
    budget: float = Field(ge=0)


class TacticalFitRequest(BaseModel):
    player_traits: dict[str, float | None]
    required_traits: dict[str, float | None]
    player_minutes: int = Field(ge=0)


class DatedMetricRequest(BaseModel):
    observed_on: date
    value: float
    minutes: int = Field(ge=0)


class DevelopmentTrendRequest(BaseModel):
    observations: list[DatedMetricRequest]


class SentimentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class ValuationAvailabilityRequest(BaseModel):
    has_licensed_targets: bool = False
    feature_as_of: date
    target_date: date


class ComparisonRequest(BaseModel):
    left_features: dict[str, float | None]
    right_features: dict[str, float | None]
    feature_weights: dict[str, float] = Field(default_factory=dict)


class NaturalLanguageSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class ScoutReportRequest(BaseModel):
    player_name: str = Field(min_length=1)
    percentiles: dict[str, float | None]
    minutes: int = Field(ge=0)
    coverage_level: str


class RecruitmentRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    positions: list[str] = Field(min_length=1)
    feature_weights: dict[str, float]
    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    feature_set_version: str = Field(min_length=1, max_length=120)


class ShortlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    role_id: int | None = Field(default=None, ge=1)


class ShortlistDecisionEvidenceRequest(BaseModel):
    reference_player_id: int = Field(ge=1)


class ShortlistPlayerRequest(BaseModel):
    player_id: int = Field(ge=1)
    rank: int | None = Field(default=None, ge=1)
    stage: Literal["IDENTIFIED", "REVIEWING", "CONTACTED", "REJECTED"] = "IDENTIFIED"
    rationale: str | None = Field(default=None, max_length=2000)
    decision_evidence: ShortlistDecisionEvidenceRequest | None = None


@app.get("/coverage/open")
def open_coverage() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    statsbomb_path = root / "data" / "coverage" / "statsbomb-open-big-five.json"
    wyscout_path = root / "data" / "coverage" / "wyscout-open-catalogue.json"
    return {
        "openfootball": openfootball_coverage(),
        "statsbomb": json.loads(statsbomb_path.read_text(encoding="utf-8")),
        "wyscout": json.loads(wyscout_path.read_text(encoding="utf-8")),
        "meta": {"data_as_of": datetime.now(UTC), "live_provider_status": "CREDENTIAL_REQUIRED"},
    }


@app.get("/coverage")
def get_coverage() -> dict[str, object]:
    rows = coverage_observations()
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "count": len(rows),
            "live_provider_status": "CREDENTIAL_REQUIRED",
        },
    }


@app.get("/coverage/{competition}/{season:path}")
def get_competition_season_coverage(competition: str, season: str) -> dict[str, object]:
    rows = coverage_observations(competition, season)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "competition": competition,
            "season": season,
            "count": len(rows),
        },
    }


@app.get("/players")
def list_players(
    search: str | None = None,
    limit: int = 50,
    position: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    min_minutes: int = 0,
    sort: str = "name",
) -> dict[str, object]:
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    if min_minutes < 0:
        raise HTTPException(status_code=422, detail="min_minutes cannot be negative")
    if position is not None and position not in {"GK", "DF", "MD", "FW"}:
        raise HTTPException(status_code=422, detail="position must be GK, DF, MD or FW")
    if sort not in {"name", "minutes", "appearances", "popular"}:
        raise HTTPException(
            status_code=422, detail="sort must be name, minutes, appearances or popular"
        )
    filters_used = bool(position or competition or season or min_minutes or sort != "name")
    rows = (
        players(search, limit, position, competition, season, min_minutes, sort)
        if filters_used
        else players(search, limit)
    )
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "coverage_level": "CANONICAL_IDENTITY",
            "count": len(rows),
            "sample_size": len(rows),
            "data_as_of": _latest_value(rows, "data_as_of"),
        },
    }


@app.get("/players/provider/{provider}/{provider_player_id}/matches/{provider_match_id}")
def get_provider_player_match_profile(
    provider: str, provider_player_id: str, provider_match_id: str
) -> dict[str, object]:
    profile = provider_player_match_profile(provider, provider_match_id, provider_player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Provider player-match profile not found")
    identity_status = str(
        profile.get("identity_status")
        or ("CANONICAL_LINKED" if profile.get("player_id") is not None else "PROVIDER_UNRESOLVED")
    )
    return {
        "data": profile,
        "meta": {
            "provider": provider,
            "identity_status": identity_status,
            "coverage_level": "EVENT_SPATIAL",
            "generated_at": datetime.now(UTC),
        },
    }


@app.get("/players/{player_id}")
def get_player(player_id: int) -> dict[str, object]:
    row = player_detail(player_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return {
        "data": row,
        "meta": {
            "generated_at": datetime.now(UTC),
            "data_as_of": row.get("updated_at"),
            "coverage_level": "CANONICAL_IDENTITY",
        },
    }


@app.get("/players/{player_id}/seasons")
def get_player_seasons(player_id: int) -> dict[str, object]:
    rows = player_seasons(player_id)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "feature_set_version": "player_style_v1",
            "count": len(rows),
            "sample_size": len(rows),
            "data_as_of": _latest_value(rows, "data_as_of"),
            "season_statuses": sorted(
                {str(row["season_status"]) for row in rows if row.get("season_status")}
            ),
        },
    }


@app.get("/players/{player_id}/news")
def get_player_news(player_id: int) -> dict[str, object]:
    rows = player_news(player_id)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "data_as_of": _latest_value(rows, "data_as_of"),
            "sample_size": len(rows),
            "source_status": "API_RIGHTS_REQUIRED",
        },
    }


@app.get("/players/{player_id}/research")
def get_player_research(player_id: int) -> dict[str, object]:
    player = player_detail(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    query = str(player["canonical_name"])
    adapter = GoogleNewsRSSAdapter()
    result = research_player(query)
    news_ok = any(s.source == "google_news_rss" and s.status == "OK" for s in result.sources)
    news_down = any(
        s.source == "google_news_rss" and s.status == "UNAVAILABLE" for s in result.sources
    )
    if news_ok:
        status, error_message = "AVAILABLE", None
    elif news_down:
        status = "SOURCE_TEMPORARILY_UNAVAILABLE"
        error_message = "The live headline source did not respond; use the linked search instead."
    else:
        status, error_message = "NO_RECENT_RESULTS", None
    return {
        "data": {
            "query": query,
            "search_url": adapter.search_url(query),
            "articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "source_url": article.source_url,
                    "published_at": article.published_at,
                    "topics": extract_topics(article.title),
                }
                for article in result.articles
            ],
            "claims": [asdict(claim) for claim in result.claims],
            "sources": result.sources_dict(),
            "retrieved_at": result.retrieved_at,
            "extractor": result.extractor,
            "disclaimer": (
                "Claims are unverified public statements with quoted evidence and a source "
                "link. Verify before use. They are never used as training targets or in "
                "performance scores."
            ),
            "error_message": error_message,
        },
        "meta": {
            "generated_at": datetime.now(UTC),
            "provider": "google_news_rss+wikipedia",
            "status": status,
            "sample_size": len(result.articles),
            "claim_count": len(result.claims),
            "content_policy": (
                "HEADLINE_METADATA_PLUS_SHORT_VERBATIM_EVIDENCE_QUOTES_FROM_ALLOWLISTED_"
                "SOURCES_(GOOGLE_NEWS_RSS,_WIKIPEDIA);_NO_TRANSFERMARKT;_NO_FULL_ARTICLES"
            ),
            "decision_use": "CURRENT_CONTEXT_RESEARCH_NOT_PERFORMANCE_SCORING",
            "label": "UNVERIFIED_PUBLIC_ESTIMATE",
        },
    }


@app.get("/players/{player_id}/sentiment")
def get_player_sentiment(player_id: int) -> dict[str, object]:
    rows = player_sentiment(player_id)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "use": "EXTERNAL_CONTEXT_ONLY",
            "source_status": "AVAILABLE_PUBLIC_APPVIEW" if rows else "NO_OBSERVATIONS",
            "data_as_of": _latest_value(rows, "data_as_of"),
            "sample_size": len(rows),
        },
    }


@app.get("/players/{player_id}/metrics")
def get_player_metrics(player_id: int) -> dict[str, object]:
    rows = player_metrics(player_id)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "feature_set_version": "player_style_v1",
            "count": len(rows),
            "sample_size": len(rows),
            "data_as_of": _latest_value(rows, "data_as_of"),
        },
    }


@app.get("/players/{player_id}/intelligence")
def get_player_intelligence(player_id: int) -> dict[str, object]:
    rows = player_intelligence(player_id)
    positions = sorted({str(row["position_group"]) for row in rows})
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "feature_set_version": "event_intelligence_v1",
            "status": "AVAILABLE" if rows else "INSUFFICIENT_EVENT_COVERAGE",
            "metric_family": "GOALKEEPER" if positions == ["GK"] else "OUTFIELD",
            "positions": positions,
            "count": len(rows),
            "sample_size": len(rows),
            "data_as_of": _latest_value(rows, "data_as_of"),
            "comparison_context": "competition, season and broad position; minimum 900 minutes",
        },
    }


@app.get("/players/{player_id}/scouting-report")
def get_player_scouting_report(
    player_id: int,
    team_id: int | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict[str, object]:
    player = player_detail(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    rows = player_intelligence(player_id)
    if not rows:
        return {
            "data": None,
            "meta": {
                "generated_at": datetime.now(UTC),
                "model_version": "explainable_scout_report_v3",
                "status": "INSUFFICIENT_EVENT_COVERAGE",
                "human_review_required": True,
            },
        }
    context = _pick_context(rows, _context(team_id, competition_id, season_id))
    context_rows = [
        row
        for row in rows
        if all(
            row.get(key) == context.get(key) for key in ("team_id", "competition_id", "season_id")
        )
    ]
    position_group = str(context.get("position_group") or "OUTFIELD")
    report_percentiles = complete_metric_family(
        {str(row["metric_name"]): float(row["percentile"]) for row in context_rows},
        position_group,
    )
    report = build_scout_report(
        player_name=str(player["canonical_name"]),
        percentiles=report_percentiles,
        minutes=int(context.get("minutes_played") or 0),
        coverage_level="EVENT_ADVANCED",
        position_group=position_group,
    )
    return {
        "data": {
            "archetype": report.archetype,
            "archetype_evidence": report.archetype_evidence,
            "archetype_description": report.archetype_description,
            "archetype_clarity": report.archetype_clarity,
            "secondary_archetype": report.secondary_archetype,
            "profile_fits": [
                {"name": name, "score": score} for name, score in report.profile_fits
            ],
            "comparison_scopes": sorted(
                {
                    str(row["comparison_scope"])
                    for row in context_rows
                    if row.get("comparison_scope")
                }
            ),
            "summary": report.summary,
            "strengths": [
                {"text": claim.text, "evidence_metrics": claim.evidence_metrics}
                for claim in report.strengths
            ],
            "risks": [
                {"text": claim.text, "evidence_metrics": claim.evidence_metrics}
                for claim in report.risks
            ],
            "caveats": report.caveats,
            "context": {
                key: context.get(key)
                for key in (
                    "team_id",
                    "team_name",
                    "competition_id",
                    "competition_name",
                    "season_id",
                    "season_label",
                    "position_group",
                    "minutes_played",
                )
            },
        },
        "meta": {
            "generated_at": datetime.now(UTC),
            "model_version": "explainable_scout_report_v3",
            "status": "AVAILABLE",
            "human_review_required": True,
            "evidence_metric_count": len(context_rows),
            "expected_metric_count": len(report_percentiles),
            "evidence_coverage_pct": round(len(context_rows) * 100 / len(report_percentiles), 1),
            "data_as_of": _latest_value(context_rows, "data_as_of"),
        },
    }


@app.get("/players/{player_id}/spatial")
def get_player_spatial(
    player_id: int,
    team_id: int | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict[str, object]:
    ctx = _context(team_id, competition_id, season_id)
    row = player_spatial(player_id, ctx) if ctx else player_spatial(player_id)
    return {
        "data": row,
        "meta": {
            "generated_at": datetime.now(UTC),
            "coverage_level": "EVENT_SPATIAL" if row else "UNAVAILABLE",
            "model_version": "contextual_event_density_v2",
            "scope": "highest-minute player-team-competition-season sample",
            "direction_note": (
                "team-relative; the team attacks left to right "
                "(99%+ of shots are in the attacking third)"
            ),
            "data_as_of": row.get("data_as_of") if row else None,
            "sample_size": int(row.get("located_event_count") or 0) if row else 0,
        },
    }


@app.get("/players/{player_id}/development")
def get_player_development(player_id: int) -> dict[str, object]:
    rows = player_intelligence(player_id)
    observations = [
        MetricDevelopmentObservation(
            metric_name=str(row["metric_name"]),
            observed_on=row["season_start_date"],
            percentile=float(row["percentile"]),
            metric_value=float(row["metric_value"]),
            minutes=int(row["minutes_played"]),
            season_label=str(row["season_label"]),
            competition_name=str(row["competition_name"]),
            team_name=str(row.get("team_name") or "Team unavailable"),
            position_group=str(row["position_group"]),
        )
        for row in rows
        if row.get("season_start_date") is not None
        and row.get("percentile") is not None
        and row.get("metric_value") is not None
    ]
    trends = metric_development_trends(observations)
    longitudinal = [trend for trend in trends if trend.observations >= 2]
    return {
        "data": [asdict(trend) for trend in trends],
        "meta": {
            "generated_at": datetime.now(UTC),
            "model_version": "observed_percentile_trajectory_v1",
            "feature_set_version": "event_intelligence_v1",
            "status": "AVAILABLE" if longitudinal else "INSUFFICIENT_LONGITUDINAL_DATA",
            "data_as_of": _latest_value(rows, "data_as_of"),
            "metric_count": len(longitudinal),
            "observation_count": len(observations),
            "interpretation": (
                "Observed movement in direction-adjusted peer percentiles; not a forecast. "
                "Competition, team role and comparison populations may change between seasons."
            ),
        },
    }


@app.get("/players/{player_id}/market")
def get_player_market(player_id: int) -> dict[str, object]:
    data = player_market(player_id)
    observations = [*data["market_values"], *data["transfers"]]
    return {
        "data": data,
        "meta": {
            "generated_at": datetime.now(UTC),
            "valuation_model_status": "LICENSED_TARGET_REQUIRED",
            "market_value_is_transfer_fee": False,
            "source_label": (
                "Third-party historical snapshot (derived from Transfermarkt), frozen at June "
                "2026. Crowd-sourced estimates, not official valuations and not current."
            ),
            "link_basis": (data.get("link") or {}).get("match_basis"),
            "data_as_of": _latest_value(observations, "data_as_of"),
            "sample_size": len(observations),
        },
    }


@app.get("/players/{player_id}/role-fit")
def get_player_role_fit(
    player_id: int,
    team_id: int | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict[str, object]:
    rows = player_intelligence(player_id)
    meta: dict[str, object] = {
        "generated_at": datetime.now(UTC),
        "model_version": "saved_role_fit_v1",
        "human_review_required": True,
    }
    if not rows:
        meta["status"] = "INSUFFICIENT_EVENT_COVERAGE"
        return {"data": [], "meta": meta}
    context = _pick_context(rows, _context(team_id, competition_id, season_id))
    context_rows = [
        row
        for row in rows
        if all(
            row.get(key) == context.get(key) for key in ("team_id", "competition_id", "season_id")
        )
    ]
    percentiles = {str(row["metric_name"]): float(row["percentile"]) for row in context_rows}
    position = str(context.get("position_group") or "")
    fits = []
    for role in recruitment_roles():
        if position not in (role.get("positions") or []):
            continue
        result = role_fit(percentiles, dict(role.get("feature_weights") or {}))
        if result is None:
            continue
        fits.append(
            {
                "role_id": role["role_id"],
                "name": role["name"],
                "fit_score": round(result.score, 1),
                "coverage_pct": round(result.coverage * 100),
                "drivers": [
                    {"metric": name, "percentile": round(value)} for name, value in result.drivers
                ],
                "gaps": [
                    {"metric": name, "percentile": round(value)} for name, value in result.gaps
                ],
            }
        )
    fits.sort(key=lambda item: item["fit_score"], reverse=True)
    meta["status"] = "AVAILABLE" if fits else "NO_MATCHING_ROLES"
    meta["context"] = {
        "team_name": context.get("team_name"),
        "season_label": context.get("season_label"),
        "position_group": position,
    }
    return {"data": fits, "meta": meta}


@app.get("/coverage/seasons")
def get_coverage_by_season() -> dict[str, object]:
    rows = coverage_by_season()
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "note": (
                "Event-level profiles come from free open data (StatsBomb Open and Wyscout Open). "
                "Recent full seasons are not openly released, so current players are covered by "
                "the separate stats tier."
            ),
        },
    }


@app.get("/discover/archetypes")
def get_archetype_catalogue() -> dict[str, object]:
    return {"data": archetype_catalogue(), "meta": {"model_version": "archetype_catalogue_v1"}}


@app.get("/discover")
def discover_players(
    position: str,
    archetype: str,
    limit: int = 12,
    season: str | None = None,
    competition: str | None = None,
) -> dict[str, object]:
    catalogue = archetype_catalogue()
    known = {item["name"] for item in catalogue.get(position, [])}
    if archetype not in known:
        raise HTTPException(status_code=422, detail="Unknown position or archetype")
    rows = discover(
        cached_index(archetype_pool),
        position=position,
        archetype=archetype,
        limit=max(1, min(limit, 30)),
        season=season,
        competition=competition,
    )
    rows = _with_values(rows)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "model_version": "archetype_discovery_v1",
            "position": position,
            "archetype": archetype,
            "sample_size": len(rows),
            "ranking": (
                "Weighted mean of position-relative percentiles over the archetype's metrics"
            ),
            "minimum_fit": 60,
            "human_review_required": True,
        },
    }


@app.get("/players/{player_id}/tactical-context")
def get_player_tactical_context(
    player_id: int,
    team_id: int | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict[str, object]:
    ctx = _context(team_id, competition_id, season_id)
    rows = team_context_rows(player_id, ctx) if ctx else team_context_rows(player_id)
    context = build_tactical_context(rows)
    meta: dict[str, object] = {
        "generated_at": datetime.now(UTC),
        "model_version": "team_style_context_v1",
        "comparison_scope": "POOLED_PROVIDER_POSITION",
        "human_review_required": True,
    }
    if context is None:
        meta["status"] = "INSUFFICIENT_SQUAD_EVIDENCE"
        return {"data": None, "meta": meta}
    meta["status"] = "AVAILABLE"
    return {
        "data": {
            "team_name": rows[0]["team_name"],
            "competition_name": rows[0]["competition_name"],
            "season_label": rows[0]["season_label"],
            "style": context.style,
            "style_strength": context.style_strength,
            "team_player_count": context.team_player_count,
            "axes": [
                {
                    "axis": axis.axis,
                    "label": axis.label,
                    "description": axis.description,
                    "team_score": axis.team_score,
                    "player_score": axis.player_score,
                    "delta": axis.delta,
                }
                for axis in context.axes
            ],
            "adds": context.adds,
            "relies": context.relies,
            "notes": context.notes,
        },
        "meta": meta,
    }


@app.get("/players/{player_id}/related-identities")
def get_related_identities(player_id: int) -> dict[str, object]:
    rows = person_members(player_id)
    return {
        "data": rows if len(rows) > 1 else [],
        "meta": {
            "generated_at": datetime.now(UTC),
            "policy": "PRESENTATION_GROUPING_ONLY",
            "message": (
                "This profile combines records from more than one data provider, matched on "
                "an identical full name (and a shared club where noted). Underlying facts are "
                "never merged: where both providers cover the same club-season the larger "
                "sample is shown, so minutes are not double-counted."
            ),
            "sample_size": len(rows),
        },
    }


@app.get("/players/{player_id}/similar")
def get_similar_players(
    player_id: int,
    role_id: int | None = None,
    team_id: int | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict[str, object]:
    ctx = _context(team_id, competition_id, season_id)
    if ctx:
        rows = similar_players(player_id, role_id=role_id, context=ctx)
    else:
        rows = (
            similar_players(player_id, role_id=role_id) if role_id else similar_players(player_id)
        )
    rows = _with_values(rows)
    return {
        "data": rows,
        "meta": {
            "generated_at": datetime.now(UTC),
            "model_version": "advanced_event_similarity_v5",
            "feature_set_version": "event_intelligence_v1",
            "comparison_population": (
                rows[0].get("comparison_population", "competition_season_position_min_900")
                if rows
                else "competition_season_position_min_900"
            ),
            "minimum_minutes": "ROLE_CONFIGURED" if role_id else 900,
            "recruitment_role_id": role_id,
            "sample_size": len(rows),
            "data_as_of": _latest_value(rows, "data_as_of"),
            "status": "AVAILABLE" if rows else "INSUFFICIENT_FEATURE_COVERAGE",
            "message": (
                "Peers use the target's strongest qualified position-specific event model. "
                "When the competition-season cohort is too small to rank fairly, the target and "
                "peers are both ranked inside a wider same-provider position pool, labelled in "
                "comparison_population. Similarity is balanced mean percentile closeness; an "
                "optional role adds a separate weighted fit component. Candidates need at "
                "least 60% feature overlap and three metrics."
            ),
        },
    }


@app.post("/recruitment/search")
def recruitment_search(request: RecruitmentRequest) -> dict[str, object]:
    candidates = [Candidate(**candidate.model_dump()) for candidate in request.candidates]
    constraints = RecruitmentConstraints(
        maximum_age=request.maximum_age,
        maximum_value=request.maximum_value,
        minimum_minutes=request.minimum_minutes,
    )
    ranked = rank_candidates(
        request.target_features, candidates, constraints, weights=request.feature_weights
    )
    return {
        "data": [
            {
                "player_id": item.candidate.player_id,
                "name": item.candidate.name,
                "similarity_score": item.similarity.score,
                "confidence": item.similarity.confidence,
                "compared_features": item.similarity.compared_features,
                "missing_features": item.similarity.missing_features,
            }
            for item in ranked
        ],
        "meta": {
            "feature_set_version": "similarity_basic_v1",
            "generated_at": datetime.now(UTC),
        },
    }


@app.post("/recruitment/replacements")
def recruitment_replacements(request: RecruitmentRequest) -> dict[str, object]:
    response = recruitment_search(request)
    meta = dict(cast(dict[str, object], response["meta"]))
    meta["workflow"] = "REPLACEMENT_FINDER"
    meta["requires_human_review"] = True
    return {"data": response["data"], "meta": meta}


@app.get("/recruitment/roles")
def get_recruitment_roles() -> dict[str, object]:
    rows = recruitment_roles()
    return {"data": rows, "meta": {"count": len(rows), "generated_at": datetime.now(UTC)}}


@app.post("/recruitment/roles")
def post_recruitment_role(request: RecruitmentRoleRequest) -> dict[str, object]:
    row = create_recruitment_role(**request.model_dump())
    return {"data": row, "meta": {"upserted": True, "generated_at": datetime.now(UTC)}}


@app.get("/shortlists")
def get_shortlists() -> dict[str, object]:
    rows = shortlists()
    return {"data": rows, "meta": {"count": len(rows), "generated_at": datetime.now(UTC)}}


@app.post("/shortlists")
def post_shortlist(request: ShortlistRequest) -> dict[str, object]:
    row = create_shortlist(request.name, request.role_id)
    return {"data": row, "meta": {"generated_at": datetime.now(UTC)}}


@app.get("/shortlists/{shortlist_id}")
def get_shortlist(shortlist_id: int) -> dict[str, object]:
    row = shortlist_detail(shortlist_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")
    role_weights = row.get("role_feature_weights") or {}
    enriched_players = []
    for candidate in row.get("players") or []:
        evidence_rows = player_intelligence(int(candidate["player_id"]))
        if not evidence_rows:
            enriched_players.append(
                {
                    **candidate,
                    "intelligence": {
                        "status": "INSUFFICIENT_EVENT_COVERAGE",
                        "role_fit_score": None,
                        "role_feature_coverage": 0,
                        "role_feature_total": len(role_weights),
                    },
                }
            )
            continue
        context = max(
            evidence_rows,
            key=lambda item: (
                int(item.get("minutes_played") or 0),
                int(item.get("season_id") or 0),
            ),
        )
        context_rows = [
            item
            for item in evidence_rows
            if all(
                item.get(key) == context.get(key)
                for key in ("team_id", "competition_id", "season_id")
            )
        ]
        percentiles: dict[str, float | None] = {
            str(item["metric_name"]): float(item["percentile"]) for item in context_rows
        }
        weighted_metrics = [
            (metric, float(weight), cast(float, percentiles[metric]))
            for metric, weight in role_weights.items()
            if metric in percentiles and percentiles[metric] is not None and float(weight) > 0
        ]
        weight_sum = sum(weight for _, weight, _ in weighted_metrics)
        role_fit = (
            sum(weight * percentile for _, weight, percentile in weighted_metrics) / weight_sum
            if weight_sum
            else None
        )
        position_group = str(context.get("position_group") or "OUTFIELD")
        report = build_scout_report(
            player_name=str(candidate["name"]),
            percentiles=complete_metric_family(percentiles, position_group),
            minutes=int(context.get("minutes_played") or 0),
            coverage_level="EVENT_ADVANCED",
            position_group=position_group,
        )
        enriched_players.append(
            {
                **candidate,
                "intelligence": {
                    "status": "AVAILABLE",
                    "archetype": report.archetype,
                    "role_fit_score": round(role_fit, 1) if role_fit is not None else None,
                    "role_feature_coverage": len(weighted_metrics),
                    "role_feature_total": len(role_weights),
                    "strongest_signal": report.strengths[0].text if report.strengths else None,
                    "main_question": report.risks[0].text if report.risks else None,
                    "context": {
                        key: context.get(key)
                        for key in (
                            "team_name",
                            "competition_name",
                            "season_label",
                            "position_group",
                            "minutes_played",
                        )
                    },
                    "data_as_of": _latest_value(context_rows, "data_as_of"),
                },
            }
        )
    for player in enriched_players:
        context = (player.get("intelligence") or {}).get("context") or {}
        player["season_label"] = context.get("season_label")
    _with_values([p for p in enriched_players if p.get("season_label")])
    row = {**row, "players": enriched_players}
    return {
        "data": row,
        "meta": {
            "generated_at": datetime.now(UTC),
            "model_version": "shortlist_evidence_v1",
            "candidate_count": len(enriched_players),
            "human_review_required": True,
        },
    }


@app.post("/shortlists/{shortlist_id}/players")
def post_shortlist_player(shortlist_id: int, request: ShortlistPlayerRequest) -> dict[str, object]:
    shortlist = shortlist_detail(shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")
    if player_detail(request.player_id) is None:
        raise HTTPException(status_code=404, detail="Player not found")
    values = request.model_dump()
    evidence_request = values.pop("decision_evidence")
    existing_ids = {
        int(item["player_id"])
        for item in shortlist.get("players") or []
        if item.get("player_id") is not None
    }
    decision_evidence = None
    if evidence_request is not None and request.player_id not in existing_ids:
        reference_player_id = int(evidence_request["reference_player_id"])
        reference = player_detail(reference_player_id)
        if reference is None:
            raise HTTPException(status_code=422, detail="Reference player not found")
        role_id = shortlist.get("role_id")
        alternatives = (
            similar_players(reference_player_id, role_id=int(role_id))
            if role_id
            else similar_players(reference_player_id)
        )
        alternative = next(
            (item for item in alternatives if int(item["player_id"]) == request.player_id),
            None,
        )
        if alternative is None:
            raise HTTPException(
                status_code=422,
                detail="Candidate is not a qualified result for this reference player and role",
            )
        differences = alternative.get("feature_differences") or {}
        ordered = sorted(
            differences.items(),
            key=lambda item: abs(float(item[1].get("difference") or 0)),
        )
        decision_evidence = {
            "captured_at": datetime.now(UTC).isoformat(),
            "model_version": alternative.get("model_version") or "advanced_event_similarity_v4",
            "reference_player_id": reference_player_id,
            "reference_player_name": str(reference["canonical_name"]),
            "similarity_score": float(alternative["similarity_score"]),
            "role_fit_score": (
                float(alternative["role_fit_score"])
                if alternative.get("role_fit_score") is not None
                else None
            ),
            "recommendation_score": float(
                alternative.get("recommendation_score") or alternative["similarity_score"]
            ),
            "feature_coverage_pct": float(alternative.get("feature_coverage_pct") or 0),
            "compared_feature_count": int(alternative.get("compared_feature_count") or 0),
            "target_feature_count": int(alternative.get("target_feature_count") or 0),
            "closest_metric": ordered[0][0] if ordered else None,
            "largest_difference_metric": ordered[-1][0] if ordered else None,
            "competition_name": alternative.get("competition_name"),
            "season_label": alternative.get("season_label"),
            "position_group": alternative.get("position_group"),
        }
    row = upsert_shortlist_player(
        shortlist_id,
        **values,
        decision_evidence=decision_evidence,
    )
    return {
        "data": row,
        "meta": {
            "generated_at": datetime.now(UTC),
            "decision_evidence": (
                "CAPTURED_FROM_SERVER_MODEL"
                if decision_evidence is not None
                else "PRESERVED_OR_NOT_REQUESTED"
            ),
        },
    }


@app.delete("/shortlists/{shortlist_id}/players/{player_id}")
def delete_shortlist_player(shortlist_id: int, player_id: int) -> dict[str, object]:
    shortlist = shortlist_detail(shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")
    if shortlist.get("status") != "ACTIVE":
        raise HTTPException(status_code=409, detail="Archived shortlists are read-only")
    row = remove_shortlist_player(shortlist_id, player_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Player is not on this shortlist")
    return {"data": row, "meta": {"generated_at": datetime.now(UTC)}}


@app.post("/shortlists/{shortlist_id}/archive")
def post_archive_shortlist(shortlist_id: int) -> dict[str, object]:
    row = archive_shortlist(shortlist_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")
    return {"data": row, "meta": {"generated_at": datetime.now(UTC)}}


@app.get("/matches/{provider}/{provider_match_id}/summary")
def get_match_summary(provider: str, provider_match_id: str) -> dict[str, object]:
    summary = match_summary(provider, provider_match_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Match not found")
    linked = int(summary.get("linked_provider_players") or 0)
    unresolved = int(summary.get("unresolved_provider_players") or 0)
    if linked and not unresolved:
        identity_status = "CANONICAL_LINKED"
    elif linked:
        identity_status = "PARTIALLY_LINKED"
    else:
        identity_status = "PROVIDER_UNRESOLVED"
    return {
        "data": summary,
        "meta": {
            "provider": provider,
            "identity_status": identity_status,
            "generated_at": datetime.now(UTC),
        },
    }


@app.post("/squad/optimize")
def squad_optimize(request: SquadOptimizationRequest) -> dict[str, object]:
    candidates = [
        SquadCandidate(
            player_id=item.player_id,
            name=item.name,
            positions=tuple(item.positions),
            cost=item.cost,
            fit_score=item.fit_score,
        )
        for item in request.candidates
    ]
    result = optimize_squad(tuple(request.needs), candidates, request.budget)
    if result is None:
        raise HTTPException(status_code=422, detail="No feasible squad selection")
    return {
        "data": {
            "assignments": [
                {
                    "need": need,
                    "player_id": candidate.player_id,
                    "name": candidate.name,
                    "cost": candidate.cost,
                    "fit_score": candidate.fit_score,
                }
                for need, candidate in result.assignments
            ],
            "total_cost": result.total_cost,
            "total_fit": result.total_fit,
            "budget_remaining": round(request.budget - result.total_cost, 2),
        },
        "meta": {
            "optimizer_version": "squad_exact_v1",
            "generated_at": datetime.now(UTC),
            "limitations": "Fit scores must be supplied by a separately validated model.",
        },
    }


@app.post("/analytics/tactical-fit")
def get_tactical_fit(request: TacticalFitRequest) -> dict[str, object]:
    fit = tactical_fit(
        request.player_traits,
        request.required_traits,
        player_minutes=request.player_minutes,
    )
    archetype, missing = classify_archetype(request.player_traits)
    return {
        "data": {
            "score": fit.score,
            "confidence": fit.confidence,
            "compared_dimensions": fit.compared_dimensions,
            "missing_dimensions": fit.missing_dimensions,
            "archetype": archetype,
            "archetype_missing_features": missing,
        },
        "meta": {"model_version": "tactical_fit_v1", "generated_at": datetime.now(UTC)},
    }


@app.post("/analytics/development-trend")
def get_development_trend(request: DevelopmentTrendRequest) -> dict[str, object]:
    result = development_trend(
        [DatedMetric(item.observed_on, item.value, item.minutes) for item in request.observations]
    )
    return {
        "data": {
            "slope_per_year": result.slope_per_year,
            "direction": result.direction,
            "observations": result.observations,
            "total_minutes": result.total_minutes,
            "confidence": result.confidence,
        },
        "meta": {"model_version": "linear_development_v1", "generated_at": datetime.now(UTC)},
    }


@app.post("/market/sentiment/score")
def get_sentiment(request: SentimentRequest) -> dict[str, object]:
    result = score_text(request.text)
    return {
        "data": {
            "score": result.score,
            "label": result.label,
            "matched_terms": result.matched_terms,
        },
        "meta": {
            "model_version": result.model_version,
            "use": "EXTERNAL_CONTEXT_ONLY",
            "generated_at": datetime.now(UTC),
        },
    }


@app.post("/market/valuation/availability")
def get_valuation_availability(request: ValuationAvailabilityRequest) -> dict[str, object]:
    status = valuation_availability(
        request.has_licensed_targets, request.feature_as_of, request.target_date
    )
    return {
        "data": {"status": status, "estimate": None, "uncertainty_interval": None},
        "meta": {
            "feature_set_version": "valuation_features_v1",
            "generated_at": datetime.now(UTC),
            "market_value_is_transfer_fee": False,
        },
    }


@app.post("/recruitment/compare")
def recruitment_compare(request: ComparisonRequest) -> dict[str, object]:
    result = compare_profiles(
        request.left_features,
        request.right_features,
        request.feature_weights,
    )
    return {
        "data": {
            "similarity_score": result.similarity.score,
            "confidence": result.similarity.confidence,
            "compared_features": result.similarity.compared_features,
            "missing_features": result.similarity.missing_features,
            "differences": [
                {
                    "metric": item.metric,
                    "left": item.left,
                    "right": item.right,
                    "difference": item.difference,
                }
                for item in result.differences
            ],
        },
        "meta": {
            "model_version": "role_weighted_similarity_v1",
            "generated_at": datetime.now(UTC),
        },
    }


@app.post("/recruitment/parse-query")
def recruitment_parse_query(request: NaturalLanguageSearchRequest) -> dict[str, object]:
    parsed = parse_scout_query(request.query)
    return {
        "data": {
            "position": parsed.position,
            "maximum_age": parsed.maximum_age,
            "maximum_value_millions": parsed.maximum_value_millions,
            "minimum_minutes": parsed.minimum_minutes,
            "traits": parsed.traits,
            "unparsed_terms": parsed.unparsed_terms,
            "requires_confirmation": True,
        },
        "meta": {
            "parser_version": "controlled_scout_query_v1",
            "generated_at": datetime.now(UTC),
            "limitations": "Parsing does not execute recruitment decisions automatically.",
        },
    }


@app.post("/analytics/scout-report")
def generate_scout_report(request: ScoutReportRequest) -> dict[str, object]:
    report = build_scout_report(
        player_name=request.player_name,
        percentiles=request.percentiles,
        minutes=request.minutes,
        coverage_level=request.coverage_level,
    )
    return {
        "data": {
            "archetype": report.archetype,
            "archetype_evidence": report.archetype_evidence,
            "summary": report.summary,
            "strengths": [
                {"text": claim.text, "evidence_metrics": claim.evidence_metrics}
                for claim in report.strengths
            ],
            "risks": [
                {"text": claim.text, "evidence_metrics": claim.evidence_metrics}
                for claim in report.risks
            ],
            "caveats": report.caveats,
        },
        "meta": {
            "model_version": "deterministic_scout_report_v1",
            "generated_at": datetime.now(UTC),
            "human_review_required": True,
        },
    }
