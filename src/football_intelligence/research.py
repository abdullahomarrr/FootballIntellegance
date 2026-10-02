"""Source-linked current-context research for a player.

Claims extracted here are UNVERIFIED public statements with a quote and a source
link. They are context for a human reader and must never feed training targets,
performance scores or model features. Allowlisted sources only: Google News RSS
(headline metadata) and the English Wikipedia API. Transfermarkt is never
fetched (ADR-005).
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from football_intelligence.providers.google_news_rss import (
    CurrentContextArticle,
    GoogleNewsRSSAdapter,
)

LABEL = "UNVERIFIED_PUBLIC_ESTIMATE"
# Wikimedia requires a descriptive User-Agent with a real contact; set RESEARCH_CONTACT.
USER_AGENT = (
    "FootballIntelligenceResearch/1.0 "
    f"({os.environ.get('RESEARCH_CONTACT', 'https://example.org/football-intelligence')}) httpx"
)
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_LLM_MODEL = "claude-haiku-4-5-20251001"
CACHE_TTL_SECONDS = 15 * 60
MAX_CLAIMS = 20
MAX_QUOTE_WORDS = 25
CATEGORIES = ("INJURY", "CONTRACT", "TRANSFER", "MARKET_VALUE", "CURRENT_CLUB", "FORM")
ALLOWED_SOURCES = ("google_news_rss", "wikipedia")

LlmCaller = Callable[[str, str], str]


@dataclass(frozen=True, slots=True)
class Claim:
    category: str
    statement: str
    value: str | None
    source_name: str
    source_url: str
    source_published_at: datetime | None
    retrieved_at: datetime
    evidence_quote: str
    extractor: str
    label: str = LABEL
    confidence: str = "LOW"


@dataclass(frozen=True, slots=True)
class SourceStatus:
    source: str
    status: str  # OK | UNAVAILABLE | NO_RESULTS
    detail: str | None = None
    item_count: int = 0


@dataclass(slots=True)
class ResearchResult:
    player_name: str
    retrieved_at: datetime
    claims: list[Claim] = field(default_factory=list)
    articles: list[CurrentContextArticle] = field(default_factory=list)
    sources: list[SourceStatus] = field(default_factory=list)
    extractor: str = "rules_v1"

    def sources_dict(self) -> list[dict[str, Any]]:
        return [asdict(source) for source in self.sources]


@dataclass(frozen=True, slots=True)
class _Doc:
    text: str
    source_name: str
    source_url: str
    published_at: datetime | None
    kind: str  # "headline" | "wikipedia"


# ---------------------------------------------------------------- helpers


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


_PARTICLES = {"jr", "jr.", "junior", "de", "da", "dos", "van", "von", "der", "di", "el", "al"}


def name_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[\s\-]+", _fold(name)) if t]


def identity_tokens(name: str) -> list[str]:
    """Tokens a text must contain (any) to be about this player."""
    tokens = name_tokens(name)
    distinctive = [t for t in tokens[1:] if t not in _PARTICLES and len(t) > 2]
    return distinctive or tokens


def mentions_player(text: str, name: str) -> bool:
    folded = _fold(text)
    if _fold(name) in folded:
        return True
    return any(re.search(rf"\b{re.escape(t)}\b", folded) for t in identity_tokens(name))


def _short_quote(text: str, anchor: int | None = None) -> str:
    """Verbatim substring of `text` with at most MAX_QUOTE_WORDS words."""
    text = text.strip()
    spans = [m.span() for m in re.finditer(r"\S+", text)]
    if len(spans) <= MAX_QUOTE_WORDS:
        return text
    first = 0
    if anchor is not None:
        idx = next((i for i, (s, e) in enumerate(spans) if e > anchor), 0)
        first = max(0, min(idx - 8, len(spans) - MAX_QUOTE_WORDS))
    last = first + MAX_QUOTE_WORDS - 1
    return text[spans[first][0] : spans[last][1]]


def _words(text: str) -> int:
    return len(text.split())


_MONEY = re.compile(
    r"(?:[€£$]\s?\d+(?:[.,]\d+)?\s?(?:m\b|mn\b|million|bn\b|billion|k\b)?"
    r"|\b\d+(?:[.,]\d+)?\s?(?:m\b|million)\s(?:euros?|pounds?|dollars?))",
    re.IGNORECASE,
)
_CONTRACT_YEAR = re.compile(
    r"(?:contract|deal|terms)\b[^.]{0,60}?\b(?:until|through|to|expires?|expiring|runs? to)\s"
    r"(?:the end of |june |july )?(?:(?:june|july)\s)?(20\d\d)",
    re.IGNORECASE,
)
_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "INJURY",
        re.compile(
            r"\b(ruled out|injur\w*|hamstring|sidelined|knock|muscle|ligament|surgery|"
            r"fitness (?:doubt|concern|test)|doubt(?:ful)? for|return(?:s|ed)? from|"
            r"back in training|comeback)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CONTRACT",
        re.compile(
            r"\b(contract|extension|extend\w*|renew\w*|release clause|expires?|expiring|"
            r"free agent|new deal)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "MARKET_VALUE",
        re.compile(r"\b(market value|valued at|valuation|worth|price tag)\b", re.IGNORECASE),
    ),
    (
        "TRANSFER",
        re.compile(
            r"\b(joins?|joined|signs?|signed|signing|agree[ds]?|bid|fee|transfer|loan|"
            r"swap|medical|move to|moves to|linked with|target)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CURRENT_CLUB",
        re.compile(
            r"\b(?:currently )?(?:plays|play|captains|is captain|has played)\b[^.]{0,80}?"
            r"\bfor (?:the )?(?:[A-Za-z ]{0,25}\b(?:club|side|team) )?(?:the )?"
            r"([A-Z][\w'\u2019.\-]*(?: [A-Z][\w'\u2019.\-]*){0,3})",
        ),
    ),
    (
        "FORM",
        re.compile(
            r"\b(scored|scores|scoring|hat-?trick|brace|assists?|netted|double|goals?)\b",
            re.IGNORECASE,
        ),
    ),
]


_FAMILY = re.compile(r"\b(brother|sister|father|mother|son|daughter|cousin|uncle)\b", re.I)


def _lead(text: str) -> str:
    """Wikipedia lead section only: the article body is mostly career history."""
    return re.split(r"\n\s*\n\s*\n|\n==", text, maxsplit=1)[0][:4000]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _classify(sentence: str, kind: str) -> tuple[str, str | None, int] | None:
    money = _MONEY.search(sentence)
    for category, pattern in _RULES:
        match = pattern.search(sentence)
        if not match:
            continue
        if kind == "wikipedia" and (
            category == "FORM" or (category == "CURRENT_CLUB" and _FAMILY.search(sentence))
        ):
            continue  # encyclopedic career totals are not current form
        if category == "MARKET_VALUE" and not money:
            continue
        value: str | None = None
        anchor = match.start()
        if category == "CONTRACT":
            year = _CONTRACT_YEAR.search(sentence)
            if year:
                value = f"until {year.group(1)}"
                anchor = year.start()
            elif money:
                value = money.group(0).strip()
        elif category == "CURRENT_CLUB":
            value = match.group(1).strip().rstrip(".,")
        elif category in {"MARKET_VALUE", "TRANSFER"} and money:
            value = money.group(0).strip()
        return category, value, anchor
    return None


def extract_claims_rules(docs: list[_Doc], player_name: str, retrieved_at: datetime) -> list[Claim]:
    claims: list[Claim] = []
    for doc in docs:
        for sentence in _sentences(doc.text):
            if not mentions_player(sentence, player_name):
                continue
            hit = _classify(sentence, doc.kind)
            if hit is None:
                continue
            category, value, anchor = hit
            quote = _short_quote(sentence, anchor)
            statement = (
                f"Listed as playing for {value}" if category == "CURRENT_CLUB" and value else quote
            )
            claims.append(
                Claim(
                    category=category,
                    statement=statement,
                    value=value,
                    source_name=doc.source_name,
                    source_url=doc.source_url,
                    source_published_at=doc.published_at,
                    retrieved_at=retrieved_at,
                    evidence_quote=quote,
                    extractor="rules_v1",
                    confidence="MEDIUM" if value and doc.kind == "wikipedia" else "LOW",
                )
            )
    return claims


# ---------------------------------------------------------------- LLM extractor

_LLM_SYSTEM = (
    "You extract factual claims about one football player from supplied public text. "
    "Use ONLY the text given. Return a JSON array (no prose) of objects with keys: "
    '"doc" (integer index), "category" (one of INJURY, CONTRACT, TRANSFER, MARKET_VALUE, '
    'CURRENT_CLUB, FORM), "statement" (short paraphrase), "value" (string or null, e.g. '
    '"€180m" or "until 2029"), "quote" (a VERBATIM excerpt of at most 25 words copied '
    "exactly from that document). Skip anything not explicitly stated or about other people."
)


def _anthropic_caller(client: httpx.Client) -> LlmCaller | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("RESEARCH_LLM_MODEL", DEFAULT_LLM_MODEL)

    def call(system: str, user: str) -> str:
        response = client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2000,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=30,
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    return call


def _openai_compatible_caller(client: httpx.Client) -> LlmCaller | None:
    """Any OpenAI-compatible chat endpoint, e.g. Ollama (http://localhost:11434/v1) or LM Studio."""
    base_url = os.environ.get("RESEARCH_LLM_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    model = os.environ.get("RESEARCH_LLM_MODEL", "llama3.2")
    api_key = os.environ.get("RESEARCH_LLM_API_KEY", "")
    effort = os.environ.get("RESEARCH_LLM_REASONING_EFFORT", "").strip()

    def call(system: str, user: str) -> str:
        headers = {"content-type": "application/json"}
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
        response = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "temperature": 0,
                **({"reasoning_effort": effort} if effort else {}),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        return str(choices[0]["message"]["content"]) if choices else ""

    return call


def _llm_caller(client: httpx.Client) -> LlmCaller | None:
    return _openai_compatible_caller(client) or _anthropic_caller(client)


def _llm_model() -> str:
    if os.environ.get("RESEARCH_LLM_BASE_URL", "").strip():
        return os.environ.get("RESEARCH_LLM_MODEL", "llama3.2")
    return os.environ.get("RESEARCH_LLM_MODEL", DEFAULT_LLM_MODEL)


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_claims_llm(
    docs: list[_Doc],
    player_name: str,
    retrieved_at: datetime,
    caller: LlmCaller,
    model: str,
) -> list[Claim]:
    """Ask the LLM for claims; keep only those whose quote is verbatim in the source."""
    listing = "\n\n".join(
        f"[{i}] ({doc.source_name}) {doc.text[:12000]}" for i, doc in enumerate(docs)
    )
    raw = caller(_LLM_SYSTEM, f"Player: {player_name}\n\nDocuments:\n{listing}")
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("LLM response contained no JSON array")
    items = json.loads(raw[start : end + 1])
    if not isinstance(items, list):
        raise ValueError("LLM response was not a list")
    claims: list[Claim] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        index, category = item.get("doc"), item.get("category")
        quote, statement = item.get("quote"), item.get("statement")
        if (
            not isinstance(index, int)
            or not 0 <= index < len(docs)
            or category not in CATEGORIES
            or not isinstance(quote, str)
            or not isinstance(statement, str)
            or not quote.strip()
            or _words(quote) > MAX_QUOTE_WORDS
        ):
            continue
        doc = docs[index]
        if _norm_ws(quote) not in _norm_ws(doc.text):  # grounding check
            continue
        if doc.kind == "headline" and not mentions_player(doc.text, player_name):
            continue
        value = item.get("value")
        claims.append(
            Claim(
                category=category,
                statement=statement.strip()[:300],
                value=value.strip() if isinstance(value, str) and value.strip() else None,
                source_name=doc.source_name,
                source_url=doc.source_url,
                source_published_at=doc.published_at,
                retrieved_at=retrieved_at,
                evidence_quote=_norm_ws(quote),
                extractor=f"llm:{model}",
                confidence="MEDIUM",
            )
        )
    return claims


# ---------------------------------------------------------------- sources


def _fetch_wikipedia(client: httpx.Client, player_name: str) -> tuple[_Doc | None, SourceStatus]:
    try:
        search = client.get(
            WIKIPEDIA_API,
            params={
                "action": "opensearch",
                "search": player_name,
                "limit": 3,
                "namespace": 0,
                "format": "json",
            },
        )
        search.raise_for_status()
        titles = search.json()[1]
        if not titles:
            return None, SourceStatus("wikipedia", "NO_RESULTS", "No Wikipedia page found")
        tokens = name_tokens(player_name)
        needed = min(2, len(tokens))
        for title in titles:
            page = client.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "prop": "extracts|revisions",
                    "explaintext": 1,
                    "rvprop": "timestamp",
                    "titles": title,
                    "redirects": 1,
                    "format": "json",
                    "formatversion": 2,
                },
            )
            page.raise_for_status()
            pages = page.json().get("query", {}).get("pages", [])
            if not pages or pages[0].get("missing"):
                continue
            entry = pages[0]
            extract = str(entry.get("extract") or "")
            head = _fold(f"{entry.get('title', '')} {extract[:600]}")
            matched = sum(1 for t in tokens if t in head)
            if matched < needed or "football" not in extract.lower():
                continue
            revisions = entry.get("revisions") or []
            published = None
            if revisions and revisions[0].get("timestamp"):
                published = datetime.fromisoformat(
                    str(revisions[0]["timestamp"]).replace("Z", "+00:00")
                )
            canonical = str(entry.get("title", title))
            url = f"https://en.wikipedia.org/wiki/{quote(canonical.replace(' ', '_'))}"
            doc = _Doc(_lead(extract), "Wikipedia", url, published, "wikipedia")
            return doc, SourceStatus("wikipedia", "OK", canonical, 1)
        return None, SourceStatus(
            "wikipedia", "NO_RESULTS", "No page confidently matched this player"
        )
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
        return None, SourceStatus("wikipedia", "UNAVAILABLE", type(error).__name__)


def _fetch_news(
    client: httpx.Client, player_name: str
) -> tuple[list[CurrentContextArticle], SourceStatus]:
    try:
        articles = GoogleNewsRSSAdapter(client).search(player_name, limit=15)
    except (httpx.HTTPError, ValueError) as error:
        return [], SourceStatus("google_news_rss", "UNAVAILABLE", type(error).__name__)
    if not articles:
        return [], SourceStatus("google_news_rss", "NO_RESULTS", "No recent headlines")
    return articles, SourceStatus("google_news_rss", "OK", None, len(articles))


def _headline_text(title: str, publisher: str) -> str:
    suffix = f" - {publisher}"
    return title[: -len(suffix)].strip() if publisher and title.endswith(suffix) else title


def _dedupe_sort(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[str, str]] = set()
    unique: list[Claim] = []
    for claim in claims:
        key = (claim.category, _fold(claim.evidence_quote)[:90])
        if key in seen:
            continue
        seen.add(key)
        unique.append(claim)
    epoch = datetime.min.replace(tzinfo=UTC)

    def recency(claim: Claim) -> datetime:
        published = claim.source_published_at
        if published is None:
            return epoch
        return published if published.tzinfo else published.replace(tzinfo=UTC)

    unique.sort(key=recency, reverse=True)
    # Encyclopedic text carries the latest-edit date; cap it so headlines stay visible.
    out: list[Claim] = []
    wiki = 0
    for claim in unique:
        if claim.source_name == "Wikipedia":
            wiki += 1
            if wiki > 8:
                continue
        out.append(claim)
    return out[:MAX_CLAIMS]


# ---------------------------------------------------------------- orchestration

_CACHE: dict[str, tuple[float, ResearchResult]] = {}


def clear_cache() -> None:
    _CACHE.clear()


def research_player(
    player_name: str,
    *,
    client: httpx.Client | None = None,
    llm_caller: LlmCaller | None = None,
    use_cache: bool = True,
) -> ResearchResult:
    key = _fold(player_name).strip()
    now_mono = time.monotonic()
    if use_cache and key in _CACHE and now_mono - _CACHE[key][0] < CACHE_TTL_SECONDS:
        return _CACHE[key][1]

    owns_client = client is None
    http = client or httpx.Client(
        timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )
    try:
        retrieved_at = datetime.now(UTC)
        articles, news_status = _fetch_news(http, player_name)
        wiki_doc, wiki_status = _fetch_wikipedia(http, player_name)
        docs: list[_Doc] = [
            _Doc(
                _headline_text(a.title, a.source),
                a.source or "Publisher unavailable",
                a.url,
                a.published_at,
                "headline",
            )
            for a in articles
        ]
        if wiki_doc is not None:
            docs.append(wiki_doc)

        claims: list[Claim] = []
        extractor = "rules_v1"
        caller = (llm_caller or _llm_caller(http)) if docs else None
        if caller is not None:
            model = _llm_model()
            try:
                claims = extract_claims_llm(docs, player_name, retrieved_at, caller, model)
                if claims:
                    extractor = f"llm:{model}"
            except Exception:  # any LLM failure falls back to deterministic rules
                claims = []
        if not claims:
            claims = extract_claims_rules(docs, player_name, retrieved_at)

        result = ResearchResult(
            player_name=player_name,
            retrieved_at=retrieved_at,
            claims=_dedupe_sort(claims),
            articles=articles,
            sources=[news_status, wiki_status],
            extractor=extractor,
        )
    finally:
        if owns_client:
            http.close()

    if any(s.status != "UNAVAILABLE" for s in result.sources):
        _CACHE[key] = (now_mono, result)
    return result


__all__ = [
    "ALLOWED_SOURCES",
    "LABEL",
    "Claim",
    "ResearchResult",
    "SourceStatus",
    "clear_cache",
    "extract_claims_llm",
    "extract_claims_rules",
    "mentions_player",
    "research_player",
]
