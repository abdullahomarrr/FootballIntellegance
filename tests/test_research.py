from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from football_intelligence import research
from football_intelligence.research import research_player

PLAYER = "Kylian Mbappé"


def _rss(items: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<item><title>{t} - Pub</title><link>https://example.com/{i}</link>"
        f'<pubDate>Mon, 28 Sep 2026 10:00:00 GMT</pubDate><source url="https://pub.example">Pub</source></item>'
        for i, (t, _) in enumerate(items)
    )
    return f'<?xml version="1.0"?><rss><channel>{body}</channel></rss>'


WIKI_EXTRACT = (
    "Kylian Mbappé is a French professional footballer who plays as a forward for "
    "Real Madrid. Mbappé signed a contract until 2029 after a transfer worth €180m."
)


def _handler(
    headlines: list[str] | None = None,
    wiki: bool = True,
    news_status: int = 200,
    wiki_status: int = 200,
    counter: list[str] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        if counter is not None:
            counter.append(request.url.host)
        assert "transfermarkt" not in request.url.host
        if request.url.host == "news.google.com":
            if news_status != 200:
                return httpx.Response(news_status)
            return httpx.Response(200, text=_rss([(h, "") for h in headlines or []]))
        if request.url.host == "en.wikipedia.org":
            if wiki_status != 200:
                return httpx.Response(wiki_status)
            if request.url.params["action"] == "opensearch":
                return httpx.Response(200, json=["q", ["Kylian Mbappé"] if wiki else [], [], []])
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": [
                            {
                                "title": "Kylian Mbappé",
                                "extract": WIKI_EXTRACT,
                                "revisions": [{"timestamp": "2026-09-30T08:00:00Z"}],
                            }
                        ]
                    }
                },
            )
        return httpx.Response(404)

    return handle


def _client(**kwargs: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(_handler(**kwargs)))  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    research.clear_cache()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_rules_extract_injury_contract_money_with_sources() -> None:
    result = research_player(
        PLAYER,
        client=_client(
            headlines=[
                "Mbappé ruled out with hamstring injury for two weeks",
                "Real Madrid value Mbappé at €180m market value",
            ]
        ),
    )
    by_cat = {c.category: c for c in result.claims}
    assert by_cat["INJURY"].source_url.startswith("https://example.com/")
    assert by_cat["MARKET_VALUE"].value == "€180m"
    assert by_cat["CONTRACT"].value == "until 2029"
    assert by_cat["CONTRACT"].source_name == "Wikipedia"
    assert by_cat["CURRENT_CLUB"].value == "Real Madrid"
    for claim in result.claims:
        assert claim.label == "UNVERIFIED_PUBLIC_ESTIMATE"
        assert claim.extractor == "rules_v1"
        assert len(claim.evidence_quote.split()) <= 25
        assert claim.retrieved_at is not None
    assert [s.status for s in result.sources] == ["OK", "OK"]


def test_disambiguation_drops_other_person_with_same_first_name() -> None:
    result = research_player(
        PLAYER,
        client=_client(
            headlines=["Kylian Smith ruled out with hamstring injury", "Mbappé scores twice"],
            wiki=False,
        ),
    )
    quotes = [c.evidence_quote for c in result.claims]
    assert all("Smith" not in q for q in quotes)
    assert any("scores twice" in q for q in quotes)


def test_llm_grounding_rejects_invented_quote() -> None:
    def fake(system: str, user: str) -> str:
        return json.dumps(
            [
                {
                    "doc": 0,
                    "category": "INJURY",
                    "statement": "Out for two weeks",
                    "value": None,
                    "quote": "Mbappé ruled out with hamstring injury",
                },
                {
                    "doc": 0,
                    "category": "TRANSFER",
                    "statement": "Invented",
                    "value": "€1bn",
                    "quote": "Mbappé agrees billion euro move to Mars",
                },
            ]
        )

    result = research_player(
        PLAYER,
        client=_client(headlines=["Mbappé ruled out with hamstring injury"], wiki=False),
        llm_caller=fake,
    )
    assert len(result.claims) == 1
    assert result.claims[0].category == "INJURY"
    assert result.claims[0].extractor.startswith("llm:")
    assert result.extractor.startswith("llm:")


def test_llm_failure_falls_back_to_rules() -> None:
    def broken(system: str, user: str) -> str:
        raise httpx.ConnectError("boom")

    result = research_player(
        PLAYER,
        client=_client(headlines=["Mbappé ruled out with hamstring injury"], wiki=False),
        llm_caller=broken,
    )
    assert result.extractor == "rules_v1"
    assert result.claims and result.claims[0].extractor == "rules_v1"


def test_cache_avoids_second_fetch() -> None:
    calls: list[str] = []
    client = _client(headlines=["Mbappé ruled out injured"], counter=calls)
    first = research_player(PLAYER, client=client)
    n = len(calls)
    second = research_player(PLAYER, client=client)
    assert second is first
    assert len(calls) == n
    research_player(PLAYER, client=client, use_cache=False)
    assert len(calls) > n


def test_source_failures_reported_not_hidden() -> None:
    result = research_player(PLAYER, client=_client(news_status=503, wiki_status=500))
    assert [s.status for s in result.sources] == ["UNAVAILABLE", "UNAVAILABLE"]
    assert result.claims == []
    # failures are not cached
    assert research.research_player.__name__ and not research._CACHE


def test_no_results_status() -> None:
    result = research_player(PLAYER, client=_client(headlines=[], wiki=False))
    assert {s.source: s.status for s in result.sources} == {
        "google_news_rss": "NO_RESULTS",
        "wikipedia": "NO_RESULTS",
    }


def test_openai_compatible_endpoint_is_used_when_configured(monkeypatch):
    import json

    import httpx

    from football_intelligence import research

    monkeypatch.setenv("RESEARCH_LLM_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("RESEARCH_LLM_MODEL", "tiny-model")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    caller = research._llm_caller(client)
    assert caller is not None
    assert caller("system text", "user text") == "[]"
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"
    assert seen["body"]["model"] == "tiny-model"
    assert seen["body"]["temperature"] == 0
    assert research._llm_model() == "tiny-model"


def test_no_llm_is_configured_by_default(monkeypatch):
    import httpx

    from football_intelligence import research

    for name in ("RESEARCH_LLM_BASE_URL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert research._llm_caller(httpx.Client()) is None
