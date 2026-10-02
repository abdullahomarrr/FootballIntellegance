from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from football_intelligence.news import NewsArticle

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTAdapter:
    provider = "gdelt_doc_2"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30, follow_redirects=True)

    def search_articles(
        self, query: str, *, max_records: int = 75, timespan: str = "3months"
    ) -> list[NewsArticle]:
        if not query.strip():
            raise ValueError("GDELT query cannot be empty")
        if not 1 <= max_records <= 250:
            raise ValueError("GDELT max_records must be between 1 and 250")
        response = self.client.get(
            BASE_URL,
            params={
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": max_records,
                "timespan": timespan,
                "sort": "datedesc",
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("articles") if isinstance(payload, dict) else None
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise ValueError("GDELT response articles must be a list")
        return [self._normalize_article(row) for row in rows]

    @staticmethod
    def _normalize_article(row: Any) -> NewsArticle:
        if not isinstance(row, dict) or not row.get("url") or not row.get("title"):
            raise ValueError("GDELT article requires url and title")
        published = None
        if row.get("seendate"):
            published = datetime.strptime(str(row["seendate"]), "%Y%m%dT%H%M%SZ")
        return NewsArticle(
            provider="gdelt_doc_2",
            provider_article_id=str(row.get("url")),
            url=str(row["url"]),
            title=str(row["title"]),
            published_at=published,
            permitted_snippet=None,
        )
