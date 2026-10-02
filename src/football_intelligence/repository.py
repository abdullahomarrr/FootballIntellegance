from __future__ import annotations

import json
import os
from typing import Any


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://football:football-local-only@localhost:5432/football_intelligence",
    )


def _query_one(query: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
    import psycopg
    from psycopg.rows import dict_row

    with (
        psycopg.connect(database_url(), row_factory=dict_row) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, parameters)
        return cursor.fetchone()


def _query_all(query: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with (
        psycopg.connect(database_url(), row_factory=dict_row) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, parameters)
        return list(cursor.fetchall())


def _execute_one(query: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
    import psycopg
    from psycopg.rows import dict_row

    with (
        psycopg.connect(database_url(), row_factory=dict_row) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, parameters)
        return cursor.fetchone()


Context = tuple[int | None, int | None, int | None]  # team_id, competition_id, season_id
PROVIDER_PREFERENCE = {"wyscout_open": 0, "statsbomb_open": 1}


def person_member_ids(player_id: int) -> list[int]:
    """Every provider identity of the same person (just the player itself if unlinked)."""
    rows = _query_all(
        """
        SELECT member.player_id
        FROM player_person me
        JOIN player_person member USING (person_id)
        WHERE me.player_id = %s
        ORDER BY member.player_id
        """,
        (player_id,),
    )
    return [int(row["player_id"]) for row in rows] or [player_id]


def _context_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (row.get("team_id"), row.get("competition_id"), row.get("season_id"))


def _best_member_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Where two provider identities cover the same club-season, keep the larger sample only."""
    owner: dict[tuple[Any, Any, Any], tuple[int, int]] = {}
    for row in rows:
        key = _context_key(row)
        rank = (-int(row.get("minutes_played") or 0), int(row["player_id"]))
        if key not in owner or rank < owner[key]:
            owner[key] = rank
    return [row for row in rows if owner[_context_key(row)][1] == int(row["player_id"])]


def _context_filter(context: Context | None) -> tuple[int | None, ...]:
    team_id, competition_id, season_id = context or (None, None, None)
    return (team_id, team_id, competition_id, competition_id, season_id, season_id)


# Editorial list: well-known players whose peak market value undersells how famous they are
# (older legends) get a boost in the default "most popular" ordering. Names are accent-free.
FEATURED_PLAYERS = [
    "lionel messi", "cristiano ronaldo", "neymar", "luka modric", "toni kroos", "gareth bale",
    "kylian mbappe", "harry kane", "mohamed salah",
    "kevin de bruyne", "karim benzema", "robert lewandowski", "andres iniesta", "xavi",
    "ronaldinho", "zlatan ibrahimovic", "sergio ramos", "eden hazard", "luis suarez",
    "wayne rooney", "paul pogba", "antoine griezmann", "manuel neuer", "virgil van dijk",
    "thomas muller", "arjen robben", "mesut ozil", "sadio mane", "angel di maria",
    "rodri", "declan rice", "franck ribery", "gerard pique", "sergio busquets", "thiago silva",
]
_ACCENTS = "áàâäãåéèêëíìîïóòôöõúùûüçñćčšžøđ"
_PLAIN = "aaaaaaeeeeiiiiooooouuuucnccszod"


def _fold_search(search: str | None) -> str:
    """Lower-case, accent-free form of a search term, as stored in dim_player.normalized_name."""
    from football_intelligence.market_snapshot import fold

    return fold(search)


def players(
    search: str | None = None,
    limit: int = 50,
    position: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    min_minutes: int = 0,
    sort: str = "name",
) -> list[dict[str, Any]]:
    pattern = f"%{search}%" if search else "%"
    folded = _fold_search(search)
    plain_pattern = f"%{folded}%" if folded else "%"
    competition_pattern = f"%{competition}%" if competition else None
    season_pattern = f"%{season}%" if season else None
    shown_name = "coalesce(p.display_name, p.canonical_name)"
    order_by = {
        "name": f"{shown_name}, p.player_id",
        "minutes": f"profile.minutes_played DESC NULLS LAST, {shown_name}",
        "appearances": f"profile.appearances DESC NULLS LAST, {shown_name}",
        # Peak market value over every record of the person: a rough, data-backed fame ranking.
        "popular": (
            "(coalesce(max(peak.peak_value), 0) + CASE WHEN translate(lower("
            f"{shown_name}), '{_ACCENTS}', '{_PLAIN}') = ANY(%s) "
            "THEN 100000000 ELSE 0 END "
            # Thin evidence (under 900 recorded minutes ever, e.g. tournament-only samples) ranks
            # lower, so the default list leads with players who have a real event history.
            "- CASE WHEN coalesce(max(history.best_minutes), 0) < 900 THEN 80000000 ELSE 0 END) "
            "DESC, profile.minutes_played DESC NULLS LAST, "
            f"{shown_name}"
        ),
    }.get(sort, f"{shown_name}, p.player_id")
    profile_required = "AND profile.player_id IS NOT NULL" if sort == "popular" else ""
    peak_cte = (
        """, peak AS (
            SELECT coalesce(pp.person_id::text, v.player_id::text) AS k,
                   max(v.amount) AS peak_value
            FROM fact_player_market_value v
            LEFT JOIN player_person pp ON pp.player_id = v.player_id
            GROUP BY 1
        ), history AS (
            SELECT coalesce(pp.person_id::text, ps.player_id::text) AS k,
                   max(ps.minutes_played) AS best_minutes
            FROM analytics.mart_player_season_profile ps
            LEFT JOIN player_person pp ON pp.player_id = ps.player_id
            GROUP BY 1
        )"""
        if sort == "popular"
        else ", peak AS (SELECT NULL::text AS k, NULL::numeric AS peak_value WHERE false)"
        ", history AS (SELECT NULL::text AS k, NULL::numeric AS best_minutes WHERE false)"
    )
    return _query_all(
        f"""
        WITH ranked_profile AS (
            SELECT ps.player_id, ps.position_group, ps.minutes_played, ps.appearances,
                   coalesce(intel.event_count, 0) AS event_count,
                   ps.sample_confidence, s.label AS season_label, s.status AS season_status,
                   c.canonical_name AS competition_name, t.canonical_name AS team_name,
                   row_number() OVER (
                       PARTITION BY coalesce(person.person_id, ps.player_id)
                       ORDER BY s.label DESC, ps.minutes_played DESC
                   ) AS profile_rank
            FROM analytics.mart_player_season_profile ps
            LEFT JOIN player_person person ON person.player_id = ps.player_id
            LEFT JOIN analytics.mart_player_season_intelligence intel
              ON intel.player_id = ps.player_id AND intel.team_id IS NOT DISTINCT FROM ps.team_id
             AND intel.competition_id = ps.competition_id AND intel.season_id = ps.season_id
            JOIN dim_season s ON s.season_id = ps.season_id
            JOIN dim_competition c ON c.competition_id = ps.competition_id
            LEFT JOIN dim_team t ON t.team_id = ps.team_id
            WHERE (%s::text IS NULL OR ps.position_group = %s)
              AND (%s::text IS NULL OR c.canonical_name ILIKE %s)
              AND (%s::text IS NULL OR s.label ILIKE %s)
              AND ps.minutes_played >= %s
        ), canonical_choice AS (
            SELECT p.player_id,
                   row_number() OVER (
                       PARTITION BY coalesce(person.person_id::text, lower(trim(p.canonical_name)))
                       ORDER BY (profile.player_id IS NOT NULL) DESC,
                                coalesce(profile.event_count, 0) DESC,
                                coalesce(profile.minutes_played, 0) DESC,
                                p.player_id
                   ) AS entity_rank
            FROM dim_player p
            LEFT JOIN player_person person ON person.player_id = p.player_id
            LEFT JOIN ranked_profile profile
              ON profile.player_id = p.player_id AND profile.profile_rank = 1
        ){peak_cte}
        SELECT p.player_id, coalesce(p.display_name, p.canonical_name) AS canonical_name,
               p.canonical_name AS legal_name, p.birth_date, p.nationality_codes,
               p.preferred_foot, p.height_cm,
               count(DISTINCT b.provider) AS provider_count,
               array_remove(array_agg(DISTINCT b.provider), NULL) AS providers,
               profile.position_group, profile.minutes_played, profile.appearances,
               profile.season_label, profile.season_status, profile.competition_name,
               profile.team_name, profile.sample_confidence,
               max(p.updated_at) AS data_as_of
        FROM dim_player p
        JOIN canonical_choice choice
          ON choice.player_id = p.player_id AND choice.entity_rank = 1
        LEFT JOIN bridge_player_provider b ON b.player_id = p.player_id AND b.valid_to IS NULL
        LEFT JOIN ranked_profile profile
          ON profile.player_id = p.player_id AND profile.profile_rank = 1
        LEFT JOIN player_person outer_person ON outer_person.player_id = p.player_id
        LEFT JOIN peak ON peak.k = coalesce(outer_person.person_id::text, p.player_id::text)
        LEFT JOIN history ON history.k = coalesce(outer_person.person_id::text, p.player_id::text)
        WHERE (p.canonical_name ILIKE %s OR p.display_name ILIKE %s OR p.normalized_name ILIKE %s)
          AND (%s::text IS NULL OR profile.position_group IS NOT NULL)
          AND (%s::text IS NULL OR profile.competition_name IS NOT NULL)
          AND (%s::text IS NULL OR profile.season_label IS NOT NULL)
          AND (%s = 0 OR profile.minutes_played IS NOT NULL)
          {profile_required}
        GROUP BY p.player_id, p.display_name, profile.position_group, profile.minutes_played,
                 profile.appearances, profile.season_label, profile.season_status,
                 profile.competition_name, profile.team_name, profile.sample_confidence
        ORDER BY {order_by}
        LIMIT %s
        """,
        (
            position,
            position,
            competition_pattern,
            competition_pattern,
            season_pattern,
            season_pattern,
            min_minutes,
            pattern,
            pattern,
            plain_pattern,
            position,
            competition_pattern,
            season_pattern,
            min_minutes,
            *([FEATURED_PLAYERS] if sort == "popular" else []),
            limit,
        ),
    )


def openfootball_coverage() -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT c.canonical_name AS competition_name,
               cp.provider_competition_id AS competition_code,
               s.label AS season,
               count(*) AS fixture_count,
               count(*) FILTER (WHERE m.status = 'FINISHED') AS finished_count,
               count(*) FILTER (WHERE m.status = 'SCHEDULED') AS scheduled_count,
               max(m.data_as_of) AS data_as_of
        FROM bridge_match_provider mp
        JOIN dim_match m USING (match_id)
        JOIN dim_competition c USING (competition_id)
        JOIN dim_season s USING (season_id)
        JOIN bridge_competition_provider cp
          ON cp.competition_id = c.competition_id AND cp.provider = mp.provider
        WHERE mp.provider = 'openfootball'
        GROUP BY c.canonical_name, cp.provider_competition_id, s.label
        ORDER BY c.canonical_name
        """,
        (),
    )


def _display(row: dict[str, Any]) -> dict[str, Any]:
    """Expose the short name as `canonical_name`; keep the legal name separately."""
    row["legal_name"] = row["canonical_name"]
    row["canonical_name"] = row.get("display_name") or row["canonical_name"]
    return row


def player_detail(player_id: int) -> dict[str, Any] | None:
    ids = person_member_ids(player_id)
    rows = _query_all(
        """
        SELECT p.*, coalesce(
            jsonb_agg(jsonb_build_object(
                'provider', b.provider,
                'provider_player_id', b.provider_player_id,
                'provider_name', b.provider_name,
                'confidence', b.confidence,
                'verified', b.verified
            )) FILTER (WHERE b.bridge_id IS NOT NULL), '[]'::jsonb
        ) AS provider_identities
        FROM dim_player p
        LEFT JOIN bridge_player_provider b ON b.player_id = p.player_id AND b.valid_to IS NULL
        WHERE p.player_id = ANY(%s)
        GROUP BY p.player_id
        """,
        (ids,),
    )
    if not rows:
        return None
    rows.sort(key=lambda row: (row["player_id"] != player_id, row["player_id"]))
    merged = dict(rows[0])
    identities: list[Any] = []
    for row in rows:
        identities.extend(row.get("provider_identities") or [])
        for field in ("birth_date", "preferred_foot", "height_cm", "display_name"):
            if merged.get(field) is None and row.get(field) is not None:
                merged[field] = row[field]
        # country names read better than three-letter codes
        codes = row.get("nationality_codes") or []
        if codes and any(len(str(code)) > 3 for code in codes):
            merged["nationality_codes"] = codes
    merged["provider_identities"] = identities
    merged["member_player_ids"] = ids
    return _display(merged)


def person_members(player_id: int) -> list[dict[str, Any]]:
    """The provider records combined into this person's profile, with how they were linked."""
    return _query_all(
        """
        SELECT member.player_id, member.link_basis, bridge.provider,
               (SELECT max(s.label) FROM analytics.mart_player_season_intelligence i
                JOIN dim_season s USING (season_id) WHERE i.player_id = member.player_id)
                   AS latest_season,
               (SELECT count(*) FROM analytics.mart_player_season_profile pr
                WHERE pr.player_id = member.player_id) AS season_count
        FROM player_person me
        JOIN player_person member USING (person_id)
        LEFT JOIN bridge_player_provider bridge
          ON bridge.player_id = member.player_id AND bridge.valid_to IS NULL
        WHERE me.player_id = %s
        ORDER BY member.player_id
        """,
        (player_id,),
    )


def player_seasons(player_id: int) -> list[dict[str, Any]]:
    rows = _query_all(
        """
        SELECT profile.*, s.label AS season_label, s.status AS season_status,
               c.canonical_name AS competition_name, t.canonical_name AS team_name,
               coalesce(intel.has_statsbomb_events, false) AS has_statsbomb_events,
               coalesce(intel.has_wyscout_events, false) AS has_wyscout_events
        FROM analytics.mart_player_season_profile profile
        JOIN dim_season s USING (season_id)
        JOIN dim_competition c USING (competition_id)
        LEFT JOIN dim_team t USING (team_id)
        LEFT JOIN analytics.mart_player_season_intelligence intel
          ON intel.player_id = profile.player_id
         AND intel.team_id IS NOT DISTINCT FROM profile.team_id
         AND intel.competition_id = profile.competition_id
         AND intel.season_id = profile.season_id
        WHERE profile.player_id = ANY(%s)
        ORDER BY s.label, c.canonical_name
        """,
        (person_member_ids(player_id),),
    )
    return _best_member_rows(rows)


def team_context_rows(player_id: int, context: Context | None = None) -> list[dict[str, Any]]:
    """Qualified outfield percentile rows for the team-season the player is best sampled in."""
    return _query_all(
        """
        WITH ctx AS (
            SELECT team_id, competition_id, season_id
            FROM analytics.mart_player_intelligence_metric_percentile
            WHERE player_id = ANY(%s) AND position_group <> 'GK' AND team_id IS NOT NULL
              AND (%s::bigint IS NULL OR team_id = %s)
              AND (%s::bigint IS NULL OR competition_id = %s)
              AND (%s::bigint IS NULL OR season_id = %s)
            ORDER BY minutes_played DESC, season_id DESC
            LIMIT 1
        )
        SELECT metric.player_id, metric.minutes_played, metric.metric_name,
               metric.pooled_percentile AS percentile,
               metric.player_id = ANY(%s) AS is_target,
               team.canonical_name AS team_name, competition.canonical_name AS competition_name,
               season.label AS season_label
        FROM analytics.mart_player_intelligence_metric_percentile metric
        JOIN ctx USING (team_id, competition_id, season_id)
        JOIN dim_team team ON team.team_id = metric.team_id
        JOIN dim_competition competition ON competition.competition_id = metric.competition_id
        JOIN dim_season season ON season.season_id = metric.season_id
        WHERE metric.pooled_percentile IS NOT NULL AND metric.position_group <> 'GK'
        """,
        (person_member_ids(player_id), *_context_filter(context), person_member_ids(player_id)),
    )


def archetype_pool() -> list[dict[str, Any]]:
    """Every qualified player-season percentile row, labelled, for style discovery."""
    return _query_all(
        """
        SELECT metric.player_id, metric.team_id, metric.competition_id, metric.season_id,
               metric.position_group, metric.minutes_played, metric.metric_name,
               metric.percentile, coalesce(player.display_name, player.canonical_name) AS name,
               coalesce(person.person_id::text, player.normalized_name) AS normalized_name,
               team.canonical_name AS team_name, competition.canonical_name AS competition_name,
               season.label AS season_label
        FROM analytics.mart_player_intelligence_metric_percentile metric
        JOIN dim_player player ON player.player_id = metric.player_id
        LEFT JOIN player_person person ON person.player_id = metric.player_id
        JOIN dim_season season ON season.season_id = metric.season_id
        JOIN dim_competition competition ON competition.competition_id = metric.competition_id
        LEFT JOIN dim_team team ON team.team_id = metric.team_id
        WHERE metric.position_group IN ('GK', 'DF', 'MD', 'FW')
        """,
        (),
    )


def coverage_by_season() -> list[dict[str, Any]]:
    """How many people have a qualified (900+ minute) event profile in each season."""
    return _query_all(
        """
        SELECT season.label AS season_label,
               count(DISTINCT coalesce(person.person_id, i.player_id))
                   FILTER (WHERE i.minutes_played >= 900) AS qualified_players,
               count(DISTINCT i.competition_id) AS competitions,
               bool_or(i.has_statsbomb_events) AS statsbomb,
               bool_or(i.has_wyscout_events) AS wyscout
        FROM analytics.mart_player_season_intelligence i
        JOIN dim_season season ON season.season_id = i.season_id
        LEFT JOIN player_person person ON person.player_id = i.player_id
        GROUP BY season.label
        HAVING count(DISTINCT coalesce(person.person_id, i.player_id))
                   FILTER (WHERE i.minutes_played >= 900) > 0
        ORDER BY season.label DESC
        """,
        (),
    )


def player_news(player_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT n.news_id, n.title, n.canonical_url, n.permitted_snippet, n.publisher,
               n.published_at, n.story_cluster_id, n.topics, link.confidence,
               link.match_method, n.data_as_of
        FROM bridge_news_player link
        JOIN fact_news n USING (news_id)
        WHERE link.player_id = %s
        ORDER BY n.published_at DESC NULLS LAST
        LIMIT %s
        """,
        (player_id, limit),
    )


def player_sentiment(player_id: int) -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT platform, aggregate_date, topic, mention_count, sentiment_mean,
               model_version, data_as_of
        FROM fact_social_aggregate
        WHERE player_id = %s
        ORDER BY aggregate_date, platform, topic
        """,
        (player_id,),
    )


def player_metrics(player_id: int) -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT player_id, team_id, competition_id, season_id, metric_name,
               metric_value, percentile, comparison_population,
               feature_set_version, data_as_of
        FROM analytics.mart_player_metric_percentile
        WHERE player_id = ANY(%s)
        ORDER BY season_id, competition_id, metric_name
        """,
        (person_member_ids(player_id),),
    )


def player_intelligence(player_id: int) -> list[dict[str, Any]]:
    rows = _query_all(
        """
        SELECT metric.player_id, metric.team_id, metric.competition_id,
               metric.season_id, metric.position_group, metric.minutes_played,
               metric.metric_name, metric.metric_value, metric.percentile,
               metric.comparison_population, metric.comparison_scope, metric.provider_pool,
               metric.higher_is_better,
               metric.feature_set_version, metric.data_as_of,
               season.label AS season_label,
               coalesce(
                   season.start_date,
                   CASE WHEN season.label ~ '^[0-9]{4}[/-]'
                        THEN make_date(left(season.label, 4)::int, 7, 1) END
               ) AS season_start_date,
               competition.canonical_name AS competition_name,
               team.canonical_name AS team_name
        FROM analytics.mart_player_intelligence_metric_percentile metric
        JOIN dim_season season USING (season_id)
        JOIN dim_competition competition USING (competition_id)
        LEFT JOIN dim_team team USING (team_id)
        WHERE metric.player_id = ANY(%s)
        ORDER BY season_start_date NULLS LAST, metric.minutes_played,
                 metric.metric_name
        """,
        (person_member_ids(player_id),),
    )
    return _best_member_rows(rows)


def similar_players(
    player_id: int,
    limit: int = 10,
    role_id: int | None = None,
    context: Context | None = None,
) -> list[dict[str, Any]]:
    """Rank peers by advanced-event percentile distance in a like-for-like population."""
    ids = person_member_ids(player_id)
    return _query_all(
        """
        WITH role_config AS (
            SELECT positions, feature_weights, hard_constraints
            FROM recruitment_role
            WHERE role_id = %s
        ), target_profile AS (
            SELECT player_id, team_id, competition_id, season_id, position_group,
                   max(minutes_played) AS minutes_played, max(data_as_of) AS data_as_of
            FROM analytics.mart_player_intelligence_metric_percentile
            WHERE player_id = ANY(%s)
              AND (%s::bigint IS NULL OR team_id = %s)
              AND (%s::bigint IS NULL OR competition_id = %s)
              AND (%s::bigint IS NULL OR season_id = %s)
              AND minutes_played >= coalesce(
                  ((SELECT hard_constraints FROM role_config)->>'minimum_minutes')::integer,
                  900
              )
              AND position_group IS NOT NULL
              AND position_group = ANY(coalesce(
                  (SELECT positions FROM role_config), ARRAY[position_group]
              ))
            GROUP BY player_id, team_id, competition_id, season_id, position_group
            ORDER BY max(minutes_played) DESC, season_id DESC, team_id
            LIMIT 1
        ), target_metrics AS (
            SELECT metric_name, percentile, metric.comparison_scope, metric.provider_pool,
                   coalesce(
                       ((SELECT feature_weights FROM role_config)->>metric.metric_name)::numeric,
                       1.0
                   ) AS feature_weight,
                   coalesce(
                       (SELECT feature_weights FROM role_config) ? metric.metric_name,
                       false
                   ) AND coalesce(
                       ((SELECT feature_weights FROM role_config)->>metric.metric_name)::numeric,
                       0
                   ) > 0 AS is_role_weighted
            FROM analytics.mart_player_intelligence_metric_percentile metric
            JOIN target_profile target USING (player_id, team_id, competition_id, season_id)
        ), candidate_metrics AS (
            SELECT metric.player_id, metric.team_id, metric.competition_id, metric.season_id,
                   metric.metric_name, metric.percentile,
                   'COMPETITION_SEASON'::text AS comparison_scope,
                   metric.minutes_played, metric.data_as_of
            FROM analytics.mart_player_intelligence_metric_percentile metric
            JOIN target_profile target
              ON metric.position_group = target.position_group
             AND metric.competition_id = target.competition_id
             AND metric.season_id = target.season_id
            WHERE NOT (metric.player_id = ANY(%s))
              AND metric.comparison_scope = 'COMPETITION_SEASON'
              AND metric.provider_pool = (SELECT tm.provider_pool FROM target_metrics tm LIMIT 1)
            UNION ALL
            SELECT metric.player_id, metric.team_id, metric.competition_id, metric.season_id,
                   metric.metric_name, metric.pooled_percentile,
                   'POOLED_PROVIDER_POSITION'::text,
                   metric.minutes_played, metric.data_as_of
            FROM analytics.mart_player_intelligence_metric_percentile metric
            JOIN target_profile target ON metric.position_group = target.position_group
            WHERE NOT (metric.player_id = ANY(%s))
              AND metric.pooled_percentile IS NOT NULL
              AND metric.provider_pool = (
                  SELECT tm.provider_pool FROM target_metrics tm
                  WHERE tm.comparison_scope = 'POOLED_PROVIDER_POSITION' LIMIT 1
              )
        ), scored AS (
            SELECT candidate.player_id, candidate.team_id,
                   candidate.competition_id, candidate.season_id,
                   bool_and(candidate.comparison_scope = 'POOLED_PROVIDER_POSITION') AS pooled_only,
                   max(candidate.minutes_played) AS minutes_played,
                   max(candidate.data_as_of) AS data_as_of,
                   count(*) AS compared_feature_count,
                   count(*) FILTER (WHERE target.is_role_weighted) AS role_weighted_feature_count,
                   count(*)::numeric / nullif((SELECT count(*) FROM target_metrics), 0)
                     AS feature_coverage,
                   sum(
                       CASE WHEN target.is_role_weighted
                            THEN target.feature_weight * candidate.percentile END
                   ) / nullif(sum(
                       CASE WHEN target.is_role_weighted
                            THEN target.feature_weight END
                   ), 0) AS role_fit_score,
                   array_agg(candidate.metric_name ORDER BY candidate.metric_name)
                     AS compared_features,
                   jsonb_object_agg(
                       candidate.metric_name,
                       jsonb_build_object(
                           'target_percentile', target.percentile,
                           'candidate_percentile', candidate.percentile,
                           'difference', round(
                               (candidate.percentile - target.percentile)::numeric, 2
                           )
                       ) ORDER BY candidate.metric_name
                   ) AS feature_differences,
                   100.0 - avg(
                       abs(target.percentile - candidate.percentile)
                   ) AS similarity_score
            FROM candidate_metrics candidate
            JOIN target_metrics target
              ON target.metric_name = candidate.metric_name
             AND target.comparison_scope = candidate.comparison_scope
            GROUP BY candidate.player_id, candidate.team_id,
                     candidate.competition_id, candidate.season_id
        )
        , result AS (
        SELECT scored.player_id, coalesce(player.display_name, player.canonical_name) AS name,
               coalesce(person.person_id::text, scored.player_id::text) AS person_key,
               scored.team_id,
               team.canonical_name AS team_name, scored.competition_id, scored.season_id,
               competition.canonical_name AS competition_name,
               season.label AS season_label,
               target.position_group, scored.minutes_played, scored.compared_feature_count,
               (SELECT count(*) FROM target_metrics) AS target_feature_count,
               round(scored.feature_coverage * 100, 1) AS feature_coverage_pct,
               scored.role_weighted_feature_count,
               round(scored.role_fit_score::numeric, 2) AS role_fit_score,
               round((CASE
                   WHEN scored.role_fit_score IS NULL THEN scored.similarity_score
                   ELSE 0.6 * scored.similarity_score + 0.4 * scored.role_fit_score
               END)::numeric, 2) AS recommendation_score,
               scored.data_as_of,
               scored.compared_features, scored.feature_differences,
               round(scored.similarity_score::numeric, 2) AS similarity_score,
               CASE
                   WHEN scored.feature_coverage >= 0.85 THEN 'HIGH'
                   WHEN scored.feature_coverage >= 0.65 THEN 'MEDIUM'
                   ELSE 'LOW'
               END AS confidence,
               CASE WHEN scored.pooled_only
                    THEN 'pooled_provider_position_min_900'
                    ELSE 'competition_season_position_min_900'
               END AS comparison_population,
               'advanced_event_similarity_v5'::text AS model_version
        FROM scored
        CROSS JOIN target_profile target
        JOIN dim_player player ON player.player_id = scored.player_id
        LEFT JOIN player_person person ON person.player_id = scored.player_id
        LEFT JOIN dim_team team ON team.team_id = scored.team_id
        JOIN dim_competition competition ON competition.competition_id = scored.competition_id
        JOIN dim_season season ON season.season_id = scored.season_id
        WHERE scored.compared_feature_count >= greatest(
                  3, ceil((SELECT count(*) FROM target_metrics) * 0.6)::integer
              )
          AND (
              NOT coalesce(
                  (SELECT hard_constraints ? 'maximum_age' FROM role_config), false
              )
              OR (
                  player.birth_date IS NOT NULL
                  AND extract(year FROM age(current_date, player.birth_date)) <=
                      ((SELECT hard_constraints FROM role_config)->>'maximum_age')::integer
              )
          )
        )
        SELECT * FROM (
            SELECT result.*, row_number() OVER (
                PARTITION BY person_key
                ORDER BY recommendation_score DESC, minutes_played DESC, player_id
            ) AS person_rank
            FROM result
        ) ranked
        WHERE person_rank = 1
        ORDER BY recommendation_score DESC, minutes_played DESC, player_id
        LIMIT %s
        """,
        (role_id, ids, *_context_filter(context), ids, ids, limit),
    )


def spatial_snapshot_enabled() -> bool:
    """Hosted deployments set SPATIAL_SNAPSHOT=1 because they ship without fact_event."""
    return os.environ.get("SPATIAL_SNAPSHOT", "").lower() in {"1", "true", "yes"}


def player_spatial(player_id: int, context: Context | None = None) -> dict[str, Any] | None:
    if spatial_snapshot_enabled():
        return player_spatial_from_snapshot(player_id, context)
    return player_spatial_live(player_id, context)


def player_spatial_from_snapshot(
    player_id: int, context: Context | None = None
) -> dict[str, Any] | None:
    """Same sample selection as the live query, served from player_spatial_snapshot."""
    row = _query_one(
        """
        SELECT snapshot.payload
        FROM analytics.mart_player_season_profile profile
        JOIN dim_season season USING (season_id)
        LEFT JOIN player_spatial_snapshot snapshot
          ON snapshot.player_id = profile.player_id
         AND snapshot.team_id IS NOT DISTINCT FROM profile.team_id
         AND snapshot.competition_id = profile.competition_id
         AND snapshot.season_id = profile.season_id
        WHERE profile.player_id = ANY(%s)
          AND (%s::bigint IS NULL OR profile.team_id = %s)
          AND (%s::bigint IS NULL OR profile.competition_id = %s)
          AND (%s::bigint IS NULL OR profile.season_id = %s)
        ORDER BY profile.minutes_played DESC, season.start_date DESC NULLS LAST
        LIMIT 1
        """,
        (person_member_ids(player_id), *_context_filter(context)),
    )
    return row["payload"] if row and row["payload"] is not None else None


def spatial_snapshot_keys() -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT player_id, team_id, competition_id, season_id
        FROM analytics.mart_player_season_profile
        ORDER BY player_id, competition_id, season_id
        """,
        (),
    )


def player_spatial_live(player_id: int, context: Context | None = None) -> dict[str, Any] | None:
    return _query_one(
        """
        WITH context AS (
            SELECT profile.player_id, profile.team_id, profile.competition_id,
                   profile.season_id, profile.minutes_played, profile.position_group,
                   season.label AS season_label, team.canonical_name AS team_name,
                   competition.canonical_name AS competition_name
            FROM analytics.mart_player_season_profile profile
            JOIN dim_season season USING (season_id)
            JOIN dim_competition competition USING (competition_id)
            LEFT JOIN dim_team team USING (team_id)
            WHERE profile.player_id = ANY(%s)
              AND (%s::bigint IS NULL OR profile.team_id = %s)
              AND (%s::bigint IS NULL OR profile.competition_id = %s)
              AND (%s::bigint IS NULL OR profile.season_id = %s)
            ORDER BY profile.minutes_played DESC, season.start_date DESC NULLS LAST
            LIMIT 1
        ), selected AS (
            SELECT event.*
            FROM fact_event event
            JOIN context ON context.player_id = event.player_id
                        AND context.team_id = event.team_id
            JOIN dim_match match ON match.match_id = event.match_id
                                AND match.competition_id = context.competition_id
                                AND match.season_id = context.season_id
        ), located AS (
            SELECT *, least(floor(normalized_x_m / 105.0 * 12), 11)::integer AS x_bin,
                      least(floor(normalized_y_m / 68.0 * 8), 7)::integer AS y_bin
            FROM selected
            WHERE normalized_x_m IS NOT NULL AND normalized_y_m IS NOT NULL
        ), cells AS (
            SELECT x_bin, y_bin, count(*) AS events
            FROM located
            GROUP BY x_bin, y_bin
        ), layer_cells AS (
            SELECT CASE
                       WHEN event_type = 'Pass' THEN 'passes'
                       WHEN event_type IN ('Carry', 'Dribble') THEN 'carries'
                       WHEN event_type IN (
                           'Pressure', 'Ball Recovery', 'Interception', 'Block',
                           'Clearance', 'Tackle'
                       ) OR (event_type = 'Duel'
                             AND (lower(coalesce(event_subtype, '')) LIKE '%%defending%%'
                                  OR event_subtype = 'Tackle'))
                           THEN 'defensive'
                       WHEN event_type = 'Shot' THEN 'shots'
                   END AS layer, x_bin, y_bin, count(*) AS events
            FROM located
            GROUP BY 1, x_bin, y_bin
        ), pass_lines AS (
            SELECT x_m, y_m, end_x_m, end_y_m, completed
            FROM (
                SELECT selected.normalized_x_m AS x_m, selected.normalized_y_m AS y_m,
                       selected.normalized_end_x_m AS end_x_m,
                       selected.normalized_end_y_m AS end_y_m,
                       (
                           (selected.provider = 'statsbomb_open' AND selected.outcome IS NULL)
                           OR (selected.provider = 'wyscout_open'
                               AND selected.qualifiers @> '{"tags":[{"id":1801}]}'::jsonb)
                       ) AS completed,
                       sqrt(power(selected.normalized_end_x_m - selected.normalized_x_m, 2)
                            + power(selected.normalized_end_y_m - selected.normalized_y_m, 2))
                           AS length_m,
                       selected.normalized_end_x_m - selected.normalized_x_m AS forward_m
                FROM selected
                WHERE selected.event_type = 'Pass'
                  AND selected.normalized_x_m IS NOT NULL AND selected.normalized_y_m IS NOT NULL
                  AND selected.normalized_end_x_m IS NOT NULL
                  AND selected.normalized_end_y_m IS NOT NULL
            ) passes
            WHERE CASE WHEN (SELECT position_group FROM context) = 'GK'
                       THEN length_m >= 30
                       ELSE forward_m >= 15 AND end_x_m >= 70 END
            ORDER BY CASE WHEN (SELECT position_group FROM context) = 'GK'
                          THEN length_m ELSE forward_m END DESC
            LIMIT 150
        ), threat_cells AS (
            SELECT x_bin, y_bin,
                   sum(greatest(0, xt_end - xt_start)) AS threat,
                   sum(xt_end - xt_start) AS net_threat,
                   count(*) AS actions
            FROM (
                SELECT x_bin, y_bin,
                       power(normalized_end_x_m / 105.0, 3)
                         * (0.65 + 0.35 * (1 - abs(normalized_end_y_m - 34) / 34.0)) AS xt_end,
                       power(normalized_x_m / 105.0, 3)
                         * (0.65 + 0.35 * (1 - abs(normalized_y_m - 34) / 34.0)) AS xt_start
                FROM located
                WHERE normalized_end_x_m IS NOT NULL AND normalized_end_y_m IS NOT NULL
                  AND (
                      event_type = 'Carry'
                      OR (event_type = 'Pass' AND (
                          (provider = 'statsbomb_open' AND outcome IS NULL)
                          OR (provider = 'wyscout_open'
                              AND qualifiers @> '{"tags":[{"id":1801}]}'::jsonb)
                      ))
                  )
            ) scored
            GROUP BY x_bin, y_bin
        ), types AS (
            SELECT event_type, count(*) AS events
            FROM selected
            GROUP BY event_type
            ORDER BY count(*) DESC, event_type
            LIMIT 10
        ), shots AS (
            SELECT normalized_x_m AS x_m, normalized_y_m AS y_m,
                   CASE WHEN provider = 'wyscout_open'
                             AND qualifiers @> '{"tags":[{"id":101}]}'::jsonb
                        THEN 'Goal' ELSE outcome END AS outcome,
                   shot_xg
            FROM selected
            WHERE event_type = 'Shot'
              AND normalized_x_m IS NOT NULL AND normalized_y_m IS NOT NULL
            ORDER BY match_id, period, minute, second
            LIMIT 500
        )
        SELECT context.*,
               (SELECT count(*) FROM selected) AS event_count,
               (SELECT count(*) FROM located) AS located_event_count,
               (SELECT avg(normalized_x_m) FROM located) AS mean_x_m,
               (SELECT avg(normalized_y_m) FROM located) AS mean_y_m,
               coalesce((SELECT jsonb_agg(jsonb_build_object(
                   'x_bin', x_bin, 'y_bin', y_bin, 'events', events
               ) ORDER BY x_bin, y_bin) FROM cells), '[]'::jsonb) AS heatmap,
               coalesce((SELECT jsonb_object_agg(layer, cells) FROM (
                   SELECT layer, jsonb_agg(jsonb_build_object(
                       'x_bin', x_bin, 'y_bin', y_bin, 'events', events
                   ) ORDER BY x_bin, y_bin) AS cells
                   FROM layer_cells WHERE layer IS NOT NULL GROUP BY layer
               ) grouped), '{}'::jsonb) AS heatmap_layers,
               coalesce((SELECT jsonb_agg(jsonb_build_object(
                   'x_bin', x_bin, 'y_bin', y_bin, 'events', round(threat::numeric, 4),
                   'net', round(net_threat::numeric, 4), 'actions', actions
               ) ORDER BY x_bin, y_bin) FROM threat_cells), '[]'::jsonb) AS threat_cells,
               (SELECT round(sum(net_threat)::numeric, 3) FROM threat_cells) AS threat_total,
               coalesce((SELECT jsonb_agg(jsonb_build_object(
                   'x_m', round(x_m, 1), 'y_m', round(y_m, 1),
                   'end_x_m', round(end_x_m, 1), 'end_y_m', round(end_y_m, 1),
                   'completed', completed
               )) FROM pass_lines), '[]'::jsonb) AS pass_lines,
               coalesce((SELECT jsonb_object_agg(event_type, events) FROM types),
                        '{}'::jsonb) AS event_type_counts,
               coalesce((SELECT jsonb_agg(jsonb_build_object(
                   'x_m', x_m, 'y_m', y_m, 'outcome', outcome, 'shot_xg', shot_xg
               )) FROM shots), '[]'::jsonb) AS shots,
               12 AS grid_columns, 8 AS grid_rows,
               (SELECT max(data_as_of) FROM selected) AS data_as_of
        FROM context
        """,
        (person_member_ids(player_id), *_context_filter(context)),
    )


def player_market(player_id: int) -> dict[str, Any]:
    ids = person_member_ids(player_id)
    values = _query_all(
        """
        SELECT provider, valuation_date, amount, currency, valuation_type,
               data_as_of, provenance_raw_object_uri
        FROM fact_player_market_value
        WHERE player_id = ANY(%s)
        ORDER BY valuation_date
        """,
        (ids,),
    )
    transfers = _query_all(
        """
        SELECT provider, provider_transfer_id, transfer_date, from_club_name, to_club_name,
               transfer_season, transfer_status, fee_amount, fee_currency, fee_disclosed,
               raw_fee_text, data_as_of
        FROM fact_transfer
        WHERE player_id = ANY(%s)
        ORDER BY transfer_date
        """,
        (ids,),
    )
    contract = _query_one(
        """
        SELECT contract_expires, club_name, observed_as_of, provider
        FROM player_contract_observation
        WHERE player_id = ANY(%s)
        ORDER BY observed_as_of DESC, contract_expires DESC
        LIMIT 1
        """,
        (ids,),
    )
    link = _query_one(
        """
        SELECT match_basis, tm_name
        FROM bridge_player_transfermarkt
        WHERE player_id = ANY(%s)
        ORDER BY (match_basis = 'NAME_AND_BIRTH_DATE') DESC, player_id
        LIMIT 1
        """,
        (ids,),
    )
    return {"market_values": values, "transfers": transfers, "contract": contract, "link": link}


def values_at_seasons(pairs: list[tuple[int, str]]) -> dict[tuple[int, str], dict[str, Any]]:
    """Latest snapshot valuation on or before the end (30 June) of each player-season."""
    if not pairs:
        return {}
    rows = _query_all(
        """
        WITH wanted AS (
            SELECT w.player_id, w.season_label,
                   make_date(left(w.season_label, 4)::int + 1, 6, 30) AS cutoff
            FROM unnest(%s::bigint[], %s::text[]) AS w(player_id, season_label)
            WHERE w.season_label ~ '^[0-9]{4}[/-]'
        )
        SELECT w.player_id, w.season_label, v.amount, v.currency, v.valuation_date
        FROM wanted w
        CROSS JOIN LATERAL (
            SELECT value.amount, value.currency, value.valuation_date
            FROM fact_player_market_value value
            WHERE value.player_id IN (
                      SELECT member.player_id FROM player_person me
                      JOIN player_person member USING (person_id)
                      WHERE me.player_id = w.player_id
                      UNION SELECT w.player_id
                  )
              AND value.valuation_date <= w.cutoff
            ORDER BY value.valuation_date DESC
            LIMIT 1
        ) v
        """,
        ([pid for pid, _ in pairs], [label for _, label in pairs]),
    )
    return {(int(row["player_id"]), str(row["season_label"])): row for row in rows}


def coverage_observations(
    competition: str | None = None, season: str | None = None
) -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT DISTINCT ON (
            provider, plan, provider_competition_id, provider_season_id, capability
        ) provider, plan, provider_competition_id, provider_season_id,
          competition_name, season_label, capability, status, checked_at,
          provider_updated_at, raw_object_uri, checksum_sha256, terms_version, notes
        FROM provider_coverage_observation
        WHERE (%s::text IS NULL OR competition_name ILIKE %s::text)
          AND (%s::text IS NULL OR season_label = %s::text)
        ORDER BY provider, plan, provider_competition_id, provider_season_id,
                 capability, checked_at DESC
        """,
        (
            competition,
            f"%{competition}%" if competition else None,
            season,
            season,
        ),
    )


def match_summary(provider: str, provider_match_id: str) -> dict[str, Any] | None:
    return _query_one(
        """
        SELECT
            provider,
            provider_match_id,
            count(*) AS event_count,
            count(normalized_x_m) AS located_event_count,
            count(*) FILTER (WHERE event_type = 'Shot') AS shots,
            count(shot_xg) AS shots_with_xg,
            count(DISTINCT provider_player_id) FILTER (
                WHERE provider_player_id IS NOT NULL
            ) AS provider_players,
            count(DISTINCT provider_player_id) FILTER (
                WHERE provider_player_id IS NOT NULL AND player_id IS NOT NULL
            ) AS linked_provider_players,
            count(DISTINCT provider_player_id) FILTER (
                WHERE provider_player_id IS NOT NULL AND player_id IS NULL
            ) AS unresolved_provider_players,
            max(data_as_of) AS data_as_of
        FROM fact_event
        WHERE provider = %s AND provider_match_id = %s
        GROUP BY provider, provider_match_id
        """,
        (provider, provider_match_id),
    )


def provider_player_match_profile(
    provider: str, provider_match_id: str, provider_player_id: str
) -> dict[str, Any] | None:
    return _query_one(
        """
        SELECT *
        FROM analytics.mart_provider_player_match_event_profile
        WHERE provider = %s AND provider_match_id = %s AND provider_player_id = %s
        """,
        (provider, provider_match_id, provider_player_id),
    )


def recruitment_roles() -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT role_id, name, positions, feature_weights, hard_constraints,
               feature_set_version, created_at, updated_at
        FROM recruitment_role ORDER BY name, role_id
        """,
        (),
    )


def create_recruitment_role(
    *,
    name: str,
    positions: list[str],
    feature_weights: dict[str, float],
    hard_constraints: dict[str, Any],
    feature_set_version: str,
) -> dict[str, Any] | None:
    return _execute_one(
        """
        INSERT INTO recruitment_role (
            name, positions, feature_weights, hard_constraints, feature_set_version
        ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s)
        ON CONFLICT (name) DO UPDATE SET
            positions=EXCLUDED.positions,
            feature_weights=EXCLUDED.feature_weights,
            hard_constraints=EXCLUDED.hard_constraints,
            feature_set_version=EXCLUDED.feature_set_version,
            updated_at=now()
        RETURNING role_id, name, positions, feature_weights, hard_constraints,
                  feature_set_version, created_at, updated_at
        """,
        (
            name,
            positions,
            json.dumps(feature_weights),
            json.dumps(hard_constraints),
            feature_set_version,
        ),
    )


def shortlists() -> list[dict[str, Any]]:
    return _query_all(
        """
        SELECT s.shortlist_id, s.name, s.role_id, r.name AS role_name,
               r.positions AS role_positions, r.feature_set_version AS role_feature_set_version,
               s.status,
               count(sp.player_id) AS player_count, s.created_at, s.updated_at
        FROM shortlist s
        LEFT JOIN recruitment_role r USING (role_id)
        LEFT JOIN shortlist_player sp USING (shortlist_id)
        GROUP BY s.shortlist_id, r.name, r.positions, r.feature_set_version
        ORDER BY s.updated_at DESC, s.shortlist_id
        """,
        (),
    )


def create_shortlist(name: str, role_id: int | None) -> dict[str, Any] | None:
    return _execute_one(
        """
        INSERT INTO shortlist (name, role_id) VALUES (%s, %s)
        RETURNING shortlist_id, name, role_id, status, created_at, updated_at
        """,
        (name, role_id),
    )


def shortlist_detail(shortlist_id: int) -> dict[str, Any] | None:
    return _query_one(
        """
        SELECT s.shortlist_id, s.name, s.role_id, r.name AS role_name,
               r.positions AS role_positions, r.feature_weights AS role_feature_weights,
               r.hard_constraints AS role_hard_constraints,
               r.feature_set_version AS role_feature_set_version, s.status,
               s.created_at, s.updated_at,
               coalesce(jsonb_agg(jsonb_build_object(
                   'player_id', p.player_id,
                   'name', coalesce(p.display_name, p.canonical_name),
                   'rank', sp.rank,
                   'stage', sp.stage,
                   'rationale', sp.rationale,
                   'decision_evidence', sp.decision_evidence,
                   'added_at', sp.added_at
               ) ORDER BY sp.rank NULLS LAST, sp.added_at)
               FILTER (WHERE sp.player_id IS NOT NULL), '[]'::jsonb) AS players
        FROM shortlist s
        LEFT JOIN recruitment_role r USING (role_id)
        LEFT JOIN shortlist_player sp USING (shortlist_id)
        LEFT JOIN dim_player p ON p.player_id=sp.player_id
        WHERE s.shortlist_id=%s
        GROUP BY s.shortlist_id, r.name, r.positions, r.feature_weights,
                 r.hard_constraints, r.feature_set_version
        """,
        (shortlist_id,),
    )


def upsert_shortlist_player(
    shortlist_id: int,
    player_id: int,
    rank: int | None,
    stage: str,
    rationale: str | None,
    decision_evidence: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return _execute_one(
        """
        INSERT INTO shortlist_player (
            shortlist_id, player_id, rank, stage, rationale, decision_evidence
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (shortlist_id, player_id) DO UPDATE SET
            rank=EXCLUDED.rank,
            stage=EXCLUDED.stage,
            rationale=EXCLUDED.rationale,
            decision_evidence=coalesce(
                EXCLUDED.decision_evidence, shortlist_player.decision_evidence
            )
        RETURNING shortlist_id, player_id, rank, stage, rationale,
                  decision_evidence, added_at
        """,
        (
            shortlist_id,
            player_id,
            rank,
            stage,
            rationale,
            json.dumps(decision_evidence) if decision_evidence is not None else None,
        ),
    )


def remove_shortlist_player(shortlist_id: int, player_id: int) -> dict[str, Any] | None:
    """Take a candidate off a shortlist. Returns the removed row, or None if it was not there."""
    return _execute_one(
        """
        DELETE FROM shortlist_player
        WHERE shortlist_id=%s AND player_id=%s
        RETURNING shortlist_id, player_id, rank, stage, rationale
        """,
        (shortlist_id, player_id),
    )


def archive_shortlist(shortlist_id: int) -> dict[str, Any] | None:
    return _execute_one(
        """
        UPDATE shortlist SET status='ARCHIVED', updated_at=now()
        WHERE shortlist_id=%s
        RETURNING shortlist_id, name, role_id, status, created_at, updated_at
        """,
        (shortlist_id,),
    )
