import httpx
import pytest
import respx

from football_intelligence.providers.bluesky import BASE_URL as BSKY_URL
from football_intelligence.providers.bluesky import BlueskyAdapter
from football_intelligence.providers.gdelt import BASE_URL as GDELT_URL
from football_intelligence.providers.gdelt import GDELTAdapter
from football_intelligence.providers.thesportsdb import BASE_URL as SPORTS_URL
from football_intelligence.providers.thesportsdb import TheSportsDBAdapter


@respx.mock
def test_thesportsdb_day_events_preserve_raw_provenance_fields():
    respx.get(f"{SPORTS_URL}/123/eventsday.php", params={"d": "2026-09-29", "s": "Soccer"}).mock(
        return_value=httpx.Response(
            200,
            json={"events": [{
                "idEvent": "9", "strEvent": "A vs B", "idLeague": "1",
                "strLeague": "League", "strHomeTeam": "A", "strAwayTeam": "B",
                "dateEvent": "2026-09-29", "intHomeScore": "2", "intAwayScore": "0",
            }]},
        )
    )
    rows = TheSportsDBAdapter().events_by_day("2026-09-29")
    assert rows[0].home_score == 2
    assert rows[0].raw["idEvent"] == "9"


@respx.mock
def test_thesportsdb_player_search_excludes_uncleared_artwork():
    respx.get(f"{SPORTS_URL}/123/searchplayers.php", params={"p": "Example Player"}).mock(
        return_value=httpx.Response(
            200,
            json={"player": [{
                "idPlayer": "44", "strPlayer": "Example Player", "strTeam": "Example FC",
                "strNationality": "Canada", "dateBorn": "2000-01-02",
                "strStatus": "Active", "strPosition": "Midfielder",
                "strThumb": "https://example.test/not-cleared.jpg",
            }]},
        )
    )
    rows = TheSportsDBAdapter().search_players("Example Player")
    assert rows[0].birth_date.isoformat() == "2000-01-02"
    assert "strThumb" not in rows[0].raw_without_artwork


@respx.mock
def test_gdelt_returns_metadata_only_news_articles():
    respx.get(GDELT_URL).mock(
        return_value=httpx.Response(200, json={"articles": [{
            "url": "https://example.com/story", "title": "Player completes transfer",
            "seendate": "20260929T120000Z", "socialimage": "https://example.com/image.jpg",
        }]})
    )
    rows = GDELTAdapter().search_articles('"Example Player"')
    assert rows[0].provider == "gdelt_doc_2"
    assert rows[0].permitted_snippet is None


@respx.mock
def test_bluesky_uses_public_appview_and_normalizes_engagement():
    respx.get(f"{BSKY_URL}/xrpc/app.bsky.feed.searchPosts").mock(
        return_value=httpx.Response(200, json={"posts": [{
            "uri": "at://did:plc:test/app.bsky.feed.post/1", "cid": "abc",
            "author": {"handle": "fan.example"},
            "record": {"text": "Excellent performance", "createdAt": "2026-09-29T12:00:00Z"},
            "likeCount": 3, "repostCount": 1,
        }]})
    )
    rows = BlueskyAdapter().search_posts('"Example Player"')
    assert rows[0].author_handle == "fan.example"
    assert rows[0].like_count == 3


@pytest.mark.parametrize("adapter", [GDELTAdapter(), BlueskyAdapter()])
def test_public_search_adapters_reject_empty_queries(adapter):
    with pytest.raises(ValueError, match="empty"):
        if isinstance(adapter, GDELTAdapter):
            adapter.search_articles(" ")
        else:
            adapter.search_posts(" ")
