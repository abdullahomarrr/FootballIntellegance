from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

COLLECTION_ID = 4415000
COLLECTION_URL = f"https://api.figshare.com/v2/collections/{COLLECTION_ID}"
ARTICLES_URL = f"https://api.figshare.com/v2/collections/{COLLECTION_ID}/articles"


class WyscoutFile(BaseModel):
    name: str
    download_url: str
    size: int
    computed_md5: str


class WyscoutArticle(BaseModel):
    article_id: int
    title: str
    doi: str
    license_name: str
    license_url: str
    published_at: datetime
    files: list[WyscoutFile]


class WyscoutCatalogue(BaseModel):
    collection_id: int
    title: str
    doi: str
    checked_at: datetime
    articles: list[WyscoutArticle]


class WyscoutOpenAdapter:
    provider = "wyscout_open"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30, follow_redirects=True)

    def _get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def discover_catalogue(self) -> WyscoutCatalogue:
        collection = self._get_json(COLLECTION_URL)
        article_summaries = self._get_json(ARTICLES_URL, params={"page_size": 1000})
        if not isinstance(collection, dict) or not isinstance(article_summaries, list):
            raise ValueError("Unexpected Figshare collection response")
        articles: list[WyscoutArticle] = []
        for summary in article_summaries:
            article = self._get_json(summary["url_public_api"])
            license_data = article.get("license") or {}
            files = [
                WyscoutFile(
                    name=item["name"],
                    download_url=item["download_url"],
                    size=item["size"],
                    computed_md5=item["computed_md5"],
                )
                for item in article.get("files", [])
            ]
            articles.append(
                WyscoutArticle(
                    article_id=article["id"],
                    title=article["title"],
                    doi=article["doi"],
                    license_name=license_data["name"],
                    license_url=license_data["url"],
                    published_at=article["published_date"],
                    files=files,
                )
            )
        return WyscoutCatalogue(
            collection_id=collection["id"],
            title=collection["title"],
            doi=collection["doi"],
            checked_at=datetime.now(UTC),
            articles=articles,
        )

    def download_verified(self, file: WyscoutFile, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        digest = hashlib.md5(usedforsecurity=False)
        size = 0
        with self.client.stream("GET", file.download_url) as response:
            response.raise_for_status()
            with temporary.open("wb") as stream:
                for chunk in response.iter_bytes():
                    stream.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        if size != file.size or digest.hexdigest() != file.computed_md5:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Checksum or size mismatch for {file.name}")
        temporary.replace(target)
        return target
