from datetime import UTC, datetime

import pytest

from football_intelligence.providers.bluesky import BlueskyAdapter, BlueskyPost
from football_intelligence.social_loader import ingest_bluesky_player, load_bluesky_posts


def post(uri="at://one", text="excellent performance", day=29):
    return BlueskyPost(
        uri=uri,
        cid=f"cid-{day}",
        author_handle="supporter.test",
        text=text,
        created_at=datetime(2026, 9, day, 12, tzinfo=UTC),
    )


class Cursor:
    def __init__(self, player_exists=True, duplicate=False):
        self.player_exists = player_exists
        self.duplicate = duplicate
        self.current = None
        self.rowcount = 0
        self.aggregate_writes = 0

    def execute(self, query, _params=()):
        compact = " ".join(query.split())
        self.current = None
        self.rowcount = 0
        if "SELECT 1 FROM dim_player" in compact:
            self.current = (1,) if self.player_exists else None
        elif "INSERT INTO source_observation" in compact:
            self.rowcount = 0 if self.duplicate else 1
        elif "INSERT INTO fact_social_aggregate" in compact:
            self.aggregate_writes += 1
            self.rowcount = 1

    def fetchone(self):
        return self.current


class Context:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return False


class Connection:
    def __init__(self, value):
        self.value = value

    def cursor(self):
        return Context(self.value)


class Adapter(BlueskyAdapter):
    def __init__(self, rows):
        self.rows = rows

    def search_posts(self, query, *, limit=50):
        assert query == "Player Name"
        assert limit == 10
        return self.rows


def test_posts_are_idempotent_and_aggregated_by_day():
    cursor = Cursor(duplicate=True)
    result = load_bluesky_posts(
        cursor,
        [post(), post("at://two", "poor display", 28)],
        player_id=7,
        query="Player Name",
        raw_object_uri="raw/posts.json",
    )
    assert result.observations_inserted == 0
    assert result.daily_aggregates_upserted == 2
    assert cursor.aggregate_writes == 2


def test_ingestion_checks_player_and_writes_raw_snapshot(tmp_path):
    result = ingest_bluesky_player(
        Connection(Cursor()),
        player_id=7,
        query="Player Name",
        limit=10,
        raw_root=tmp_path,
        adapter=Adapter([post()]),
    )
    assert result.posts_seen == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_ingestion_rejects_missing_canonical_player(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        ingest_bluesky_player(
            Connection(Cursor(player_exists=False)),
            player_id=404,
            query="Player Name",
            limit=10,
            raw_root=tmp_path,
            adapter=Adapter([]),
        )
