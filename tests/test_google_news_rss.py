from datetime import UTC, datetime

import httpx

from football_intelligence.news import extract_topics
from football_intelligence.providers.google_news_rss import GoogleNewsRSSAdapter


def test_google_news_rss_returns_source_linked_metadata_only():
    xml = b"""<?xml version="1.0"?><rss><channel><item>
      <title>Player update - Example Publisher</title>
      <link>https://news.google.com/rss/articles/example</link>
      <pubDate>Wed, 30 Sep 2026 12:00:00 GMT</pubDate>
      <source url="https://publisher.example">Example Publisher</source>
    </item></channel></rss>"""
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml))
    )
    rows = GoogleNewsRSSAdapter(client).search("Example Player", limit=5)
    assert rows[0].source == "Example Publisher"
    assert rows[0].source_url == "https://publisher.example"
    assert rows[0].published_at == datetime(2026, 9, 30, 12, tzinfo=UTC)
    assert not hasattr(rows[0], "article_body")


def test_google_news_rss_validates_query_and_builds_research_link():
    adapter = GoogleNewsRSSAdapter(httpx.Client())
    assert "Example+Player" in adapter.search_url("Example Player")
    try:
        adapter.search("")
    except ValueError as error:
        assert "empty" in str(error)
    else:
        raise AssertionError("Expected an empty query to fail")


def test_headline_topics_use_word_boundaries_instead_of_substrings():
    assert extract_topics("Former teammate discusses player") == ()
    assert extract_topics("Player form improves after ankle injury") == (
        "INJURY",
        "PERFORMANCE",
    )
