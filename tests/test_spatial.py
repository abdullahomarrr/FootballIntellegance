import pytest

from football_intelligence.events import CanonicalEvent
from football_intelligence.spatial import build_spatial_profile, load_canonical_jsonl


def event(event_id: str, player_id: str | None, x: float | None, y: float | None):
    return CanonicalEvent(
        provider="test",
        provider_event_id=event_id,
        provider_match_id="m1",
        provider_player_id=player_id,
        provider_team_id="t1",
        period=1,
        minute=1,
        second=1,
        event_type="Pass",
        event_subtype=None,
        outcome=None,
        raw_x=x,
        raw_y=y,
        raw_end_x=None,
        raw_end_y=None,
        coordinate_system="wyscout_0_100",
        normalized_x_m=x,
        normalized_y_m=y,
        normalized_end_x_m=None,
        normalized_end_y_m=None,
        shot_xg=None,
        qualifiers={},
    )


def test_spatial_profile_bins_boundaries_and_preserves_missing():
    profile = build_spatial_profile(
        [event("1", "p1", 0, 0), event("2", "p1", 105, 68), event("3", "p1", None, None)],
        "p1",
    )
    assert profile.event_count == 3
    assert profile.located_event_count == 2
    assert [(cell.x_bin, cell.y_bin) for cell in profile.heatmap] == [(0, 0), (11, 7)]


def test_spatial_profile_rejects_invalid_grid():
    with pytest.raises(ValueError, match="positive"):
        build_spatial_profile([], "p1", grid_columns=0)


def test_load_jsonl(tmp_path):
    item = event("1", "p1", 10, 20)
    path = tmp_path / "events.jsonl"
    path.write_text(item.model_dump_json() + "\n", encoding="utf-8")
    assert load_canonical_jsonl(path) == [item]
