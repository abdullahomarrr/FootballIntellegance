from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol


class AuditCursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...

    def fetchone(self) -> tuple[Any, ...] | None: ...


def _row(cursor: AuditCursor, query: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cursor.execute(query, params)
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Final audit query unexpectedly returned no row")
    return row


def collect_final_evidence(cursor: AuditCursor) -> dict[str, Any]:
    """Collect final-test counts directly from the canonical database and dbt marts."""
    league_count, season_count, earliest_season, match_count, event_count = _row(
        cursor,
        """
        SELECT count(DISTINCT competition_id), count(DISTINCT season_id), min(season.label),
               count(DISTINCT match.match_id), count(event.event_id)
        FROM dim_match match
        JOIN dim_season season USING (season_id)
        LEFT JOIN fact_event event ON event.match_id=match.match_id
        """,
    )
    canonical_players, provider_identities = _row(
        cursor,
        """
        SELECT (SELECT count(*) FROM dim_player),
               (SELECT count(*) FROM bridge_player_provider WHERE valid_to IS NULL)
        """,
    )
    participant_identities, resolved_participant_identities = _row(
        cursor,
        """
        WITH participants AS (
          SELECT DISTINCT provider, provider_player_id
          FROM fact_event WHERE provider_player_id IS NOT NULL
        )
        SELECT count(*), count(bridge.bridge_id)
        FROM participants participant
        LEFT JOIN bridge_player_provider bridge
          ON bridge.provider=participant.provider
         AND bridge.provider_player_id=participant.provider_player_id
         AND bridge.valid_to IS NULL
        """,
    )
    profiles, qualified_profiles = _row(
        cursor,
        """
        SELECT count(*), count(*) FILTER (WHERE minutes_played >= 900)
        FROM analytics.mart_player_season_profile
        """,
    )
    (spatial_player_seasons,) = _row(
        cursor,
        """
        SELECT count(*) FROM (
          SELECT DISTINCT event.player_id, match.competition_id, match.season_id
          FROM fact_event event
          JOIN dim_match match USING (match_id)
          WHERE event.player_id IS NOT NULL
            AND event.normalized_x_m IS NOT NULL
            AND event.normalized_y_m IS NOT NULL
        ) covered
        """,
    )
    transfers, market_values, news, social_aggregates = _row(
        cursor,
        """
        SELECT (SELECT count(*) FROM fact_transfer),
               (SELECT count(*) FROM fact_player_market_value),
               (SELECT count(*) FROM fact_news),
               (SELECT count(*) FROM fact_social_aggregate)
        """,
    )
    current_matches, current_latest = _row(
        cursor,
        """
        SELECT count(match.match_id), max(match.data_as_of)
        FROM dim_season season
        LEFT JOIN dim_match match USING (season_id)
        WHERE season.label=%s
        """,
        ("2026/27",),
    )
    participants = int(participant_identities)
    resolved = int(resolved_participant_identities)
    resolution_rate = round(resolved * 100 / participants, 4) if participants else None
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "database": {
            "leagues_populated": int(league_count),
            "seasons_populated": int(season_count),
            "earliest_season": earliest_season,
            "matches": int(match_count),
            "events": int(event_count),
            "canonical_players": int(canonical_players),
            "active_provider_identity_bridges": int(provider_identities),
            "event_participant_identities": participants,
            "resolved_event_participant_identities": resolved,
            "event_participant_resolution_percent": resolution_rate,
            "player_season_profiles": int(profiles),
            "qualified_player_season_profiles": int(qualified_profiles),
            "spatial_player_seasons": int(spatial_player_seasons),
            "transfers": int(transfers),
            "market_values": int(market_values),
            "news_articles": int(news),
            "social_aggregates": int(social_aggregates),
        },
        "current_season": {
            "label": "2026/27",
            "matches": int(current_matches),
            "latest_data_as_of": current_latest.isoformat() if current_latest else None,
            "updating": bool(current_matches and current_latest),
        },
        "definitions": {
            "league": "distinct competition_id represented in dim_match",
            "season": "distinct season_id represented in dim_match",
            "identity_resolution_denominator": (
                "distinct (provider, provider_player_id) pairs present in fact_event"
            ),
            "spatial_player_season": (
                "distinct canonical player, competition and season with at least one event "
                "having both normalized coordinates"
            ),
            "qualified_profile": "mart_player_season_profile row with at least 900 minutes",
        },
    }
