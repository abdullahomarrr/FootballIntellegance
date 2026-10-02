from datetime import UTC, datetime

from football_intelligence.news import (
    NewsArticle,
    canonicalize_url,
    duplicate_score,
    enrich_article,
    extract_topics,
)


def article(url: str, title: str) -> NewsArticle:
    return NewsArticle("fixture", "1", url, title, datetime(2026, 1, 1, tzinfo=UTC))


def test_url_canonicalization_removes_tracking_but_preserves_semantic_query():
    value = canonicalize_url("HTTPS://Example.com/story/?utm_source=x&id=2#fragment")
    assert value == "https://example.com/story?id=2"


def test_news_deduplication_prefers_canonical_url_then_title_similarity():
    first = article("https://example.com/a?utm_source=x", "Player completes transfer")
    same = article("https://example.com/a", "Different syndicated title")
    similar = article("https://other.test/b", "Player completes the transfer")
    assert duplicate_score(first, same) == 1
    assert duplicate_score(first, similar) > 0.9


def test_enrichment_links_only_exact_aliases_and_tags_topics():
    enriched = enrich_article(
        article("https://example.com/a", "Eden Hazard transfer and injury update"),
        {10: ("Eden Hazard", "Hazard"), 11: ("Eden",)},
    )
    assert enriched.topics == ("INJURY", "TRANSFER")
    assert [mention.player_id for mention in enriched.mentions] == [10]
    assert enriched.mentions[0].match_method == "EXACT_ALIAS"
    assert extract_topics("unrelated weather") == ()
