import pytest

from football_intelligence.optimization import SquadCandidate, optimize_squad


def test_optimizer_maximizes_fit_under_budget_and_unique_players():
    candidates = [
        SquadCandidate(1, "Elite winger", ("RW",), 60, 95),
        SquadCandidate(2, "Value winger", ("RW",), 30, 80),
        SquadCandidate(3, "Striker", ("ST",), 40, 90),
        SquadCandidate(4, "Flexible", ("RW", "ST"), 35, 82),
    ]
    result = optimize_squad(("RW", "ST"), candidates, 75)
    assert result is not None
    assert result.total_cost == 75
    assert result.total_fit == 172
    assert {candidate.player_id for _, candidate in result.assignments} == {3, 4}


def test_optimizer_returns_none_when_need_cannot_be_filled():
    assert optimize_squad(("GK",), [], 10) is None


def test_optimizer_rejects_negative_budget():
    with pytest.raises(ValueError, match="negative"):
        optimize_squad((), [], -1)
