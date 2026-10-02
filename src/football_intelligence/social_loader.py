from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from football_intelligence.providers.bluesky import BlueskyAdapter, BlueskyPost
from football_intelligence.raw_store import FileRawStore
from football_intelligence.sentiment import score_text


@dataclass(frozen=True)
class BlueskyLoadResult:
    player_id: int
    query: str
    posts_seen: int
    observations_inserted: int
    daily_aggregates_upserted: int


def _post_payload(post: BlueskyPost) -> dict[str, Any]:
    return post.model_dump(mode="json")


def load_bluesky_posts(
    cursor: Any,
    posts: list[BlueskyPost],
    *,
    player_id: int,
    query: str,
    raw_object_uri: str,
) -> BlueskyLoadResult:
    observations = 0
    by_day: dict[date, list[float]] = {}
    for post in posts:
        payload = _post_payload(post)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        cursor.execute(
            """INSERT INTO source_observation (provider,entity_type,provider_entity_id,
               observed_at,source_url,source_license,raw_object_uri,content_hash,payload)
               VALUES ('bluesky','SOCIAL_POST',%s,%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT DO NOTHING""",
            (
                post.uri,
                post.created_at,
                post.uri,
                "Bluesky public AppView terms",
                raw_object_uri,
                sha256(encoded).hexdigest(),
                encoded.decode(),
            ),
        )
        observations += max(cursor.rowcount, 0)
        by_day.setdefault(post.created_at.date(), []).append(score_text(post.text).score)
    for day, scores in by_day.items():
        cursor.execute(
            """INSERT INTO fact_social_aggregate (platform,player_id,aggregate_date,topic,
               mention_count,sentiment_mean,model_version,data_as_of)
               VALUES ('bluesky',%s,%s,%s,%s,%s,'football_lexicon_v1',now())
               ON CONFLICT (platform,player_id,aggregate_date,topic) DO UPDATE SET
                 mention_count=EXCLUDED.mention_count,
                 sentiment_mean=EXCLUDED.sentiment_mean,
                 model_version=EXCLUDED.model_version,data_as_of=EXCLUDED.data_as_of""",
            (player_id, day, query, len(scores), sum(scores) / len(scores)),
        )
    return BlueskyLoadResult(player_id, query, len(posts), observations, len(by_day))


def ingest_bluesky_player(
    connection: Any,
    *,
    player_id: int,
    query: str,
    raw_root: Path,
    limit: int = 100,
    adapter: BlueskyAdapter | None = None,
) -> BlueskyLoadResult:
    source = adapter or BlueskyAdapter()
    posts = source.search_posts(query, limit=limit)
    payload = [_post_payload(post) for post in posts]
    manifest = FileRawStore(raw_root).write_json(
        provider="bluesky",
        endpoint="app.bsky.feed.searchPosts",
        parameters={"q": query, "limit": limit, "sort": "latest"},
        payload=payload,
        pipeline_run_id=str(uuid4()),
        schema_version="app.bsky.feed.searchPosts_v1",
        terms_version="public-appview-2026-09",
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM dim_player WHERE player_id=%s", (player_id,))
        if cursor.fetchone() is None:
            raise ValueError(f"Canonical player {player_id} does not exist")
        return load_bluesky_posts(
            cursor,
            posts,
            player_id=player_id,
            query=query,
            raw_object_uri=manifest.object_uri,
        )
