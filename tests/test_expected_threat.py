import pytest

from football_intelligence.expected_threat import ExpectedThreatModel
from tests.test_spatial import event


def test_xt_rewards_successful_progression_and_aggregates_by_player():
    model = ExpectedThreatModel()
    move = event("1", "p1", 20, 34).model_copy(
        update={"normalized_end_x_m": 90, "normalized_end_y_m": 34}
    )
    scored = model.score_event(move)
    assert scored is not None
    assert scored.xt_added > 0
    assert model.player_totals([move]) == {"p1": scored.xt_added}


def test_xt_skips_failed_or_unlocated_moves_and_rejects_bad_pitch_point():
    model = ExpectedThreatModel()
    failed = event("1", "p1", 20, 34).model_copy(
        update={
            "normalized_end_x_m": 90,
            "normalized_end_y_m": 34,
            "outcome": "Incomplete",
        }
    )
    assert model.score_event(failed) is None
    assert model.score_event(event("2", "p1", 20, 34)) is None
    with pytest.raises(ValueError, match="105x68"):
        model.value(106, 34)
