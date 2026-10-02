from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

BASE_URL = "https://api.bsky.app"


class BlueskyPost(BaseModel):
    uri: str
    cid: str
    author_handle: str
    text: str
    created_at: datetime
    like_count: int = 0
    repost_count: int = 0
    reply_count: int = 0
    quote_count: int = 0


class BlueskyAdapter:
    provider = "bluesky_public_appview"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(base_url=BASE_URL, timeout=30)

    def search_posts(self, query: str, *, limit: int = 50) -> list[BlueskyPost]:
        if not query.strip():
            raise ValueError("Bluesky query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("Bluesky limit must be between 1 and 100")
        response = self.client.get(
            "/xrpc/app.bsky.feed.searchPosts", params={"q": query, "limit": limit, "sort": "latest"}
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("posts") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Bluesky response must contain a posts list")
        return [self._normalize_post(row) for row in rows]

    @staticmethod
    def _normalize_post(row: Any) -> BlueskyPost:
        if not isinstance(row, dict):
            raise ValueError("Bluesky post must be an object")
        record = row.get("record") or {}
        author = row.get("author") or {}
        return BlueskyPost(
            uri=str(row["uri"]),
            cid=str(row["cid"]),
            author_handle=str(author["handle"]),
            text=str(record["text"]),
            created_at=datetime.fromisoformat(str(record["createdAt"]).replace("Z", "+00:00")),
            like_count=int(row.get("likeCount") or 0),
            repost_count=int(row.get("repostCount") or 0),
            reply_count=int(row.get("replyCount") or 0),
            quote_count=int(row.get("quoteCount") or 0),
        )
