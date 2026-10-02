from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

BASE_URL = "https://news.google.com/rss/search"


@dataclass(frozen=True, slots=True)
class CurrentContextArticle:
    title: str
    url: str
    source: str
    source_url: str | None
    published_at: datetime | None


class GoogleNewsRSSAdapter:
    """Read public RSS metadata without copying publisher article content."""

    provider = "google_news_rss"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=8, follow_redirects=True)

    @staticmethod
    def search_url(query: str) -> str:
        return (
            "https://news.google.com/search?q="
            f"{quote_plus(query)}&hl=en-GB&gl=GB&ceid=GB%3Aen"
        )

    def search(self, query: str, *, limit: int = 12) -> list[CurrentContextArticle]:
        if not query.strip():
            raise ValueError("News query cannot be empty")
        if not 1 <= limit <= 30:
            raise ValueError("News result limit must be between 1 and 30")
        response = self.client.get(
            BASE_URL,
            params={"q": f'"{query.strip()}"', "hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
        )
        response.raise_for_status()
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as error:
            raise ValueError("News RSS response was not valid XML") from error
        results: list[CurrentContextArticle] = []
        seen: set[str] = set()
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            source_node = item.find("source")
            source = ((source_node.text if source_node is not None else "") or "").strip()
            source_url = source_node.get("url") if source_node is not None else None
            if not title or not url or url in seen:
                continue
            seen.add(url)
            published_at = None
            if published := item.findtext("pubDate"):
                try:
                    published_at = parsedate_to_datetime(published)
                except (TypeError, ValueError):
                    published_at = None
            results.append(
                CurrentContextArticle(
                    title,
                    url,
                    source or "Publisher unavailable",
                    source_url,
                    published_at,
                )
            )
            if len(results) >= limit:
                break
        return results
