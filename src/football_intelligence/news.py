from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
TOPIC_TERMS = {
    "INJURY": {"injury", "injured", "fitness", "hamstring", "ankle"},
    "TRANSFER": {"transfer", "signing", "bid", "contract", "fee"},
    "PERFORMANCE": {"goal", "assist", "performance", "match", "form"},
    "DISCIPLINE": {"suspended", "ban", "red card", "disciplinary"},
}


@dataclass(frozen=True)
class NewsArticle:
    provider: str
    provider_article_id: str
    url: str
    title: str
    published_at: datetime | None
    permitted_snippet: str | None = None


@dataclass(frozen=True)
class EntityMention:
    player_id: int
    alias: str
    confidence: float
    match_method: str


@dataclass(frozen=True)
class EnrichedArticle:
    article: NewsArticle
    canonical_url: str
    story_cluster_id: str
    topics: tuple[str, ...]
    mentions: tuple[EntityMention, ...]


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_PARAMETERS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), "")
    )


def normalized_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.casefold()))


def story_cluster_id(title: str) -> str:
    return hashlib.sha256(normalized_title(title).encode()).hexdigest()[:20]


def duplicate_score(left: NewsArticle, right: NewsArticle) -> float:
    if canonicalize_url(left.url) == canonicalize_url(right.url):
        return 1.0
    matcher = SequenceMatcher(None, normalized_title(left.title), normalized_title(right.title))
    return round(matcher.ratio(), 4)


def extract_topics(text: str) -> tuple[str, ...]:
    normalized = f" {normalized_title(text)} "
    return tuple(
        topic
        for topic, terms in TOPIC_TERMS.items()
        if any(f" {normalized_title(term)} " in normalized for term in terms)
    )


def link_players(text: str, aliases: dict[int, tuple[str, ...]]) -> tuple[EntityMention, ...]:
    normalized = f" {normalized_title(text)} "
    mentions: list[EntityMention] = []
    for player_id, player_aliases in aliases.items():
        matches = [
            alias
            for alias in player_aliases
            if len(normalized_title(alias).split()) >= 2
            and f" {normalized_title(alias)} " in normalized
        ]
        if len(matches) == 1:
            mentions.append(EntityMention(player_id, matches[0], 1.0, "EXACT_ALIAS"))
        elif len(matches) > 1:
            mentions.append(
                EntityMention(player_id, max(matches, key=len), 1.0, "MULTIPLE_EXACT_ALIASES")
            )
    return tuple(sorted(mentions, key=lambda item: item.player_id))


def enrich_article(article: NewsArticle, aliases: dict[int, tuple[str, ...]]) -> EnrichedArticle:
    text = f"{article.title} {article.permitted_snippet or ''}"
    return EnrichedArticle(
        article=article,
        canonical_url=canonicalize_url(article.url),
        story_cluster_id=story_cluster_id(article.title),
        topics=extract_topics(text),
        mentions=link_players(text, aliases),
    )
