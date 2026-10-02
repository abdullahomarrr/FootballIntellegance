from datetime import date

from football_intelligence.entity_resolution import (
    PlayerIdentity,
    compare_players,
    normalize_name,
)


def test_name_normalization_handles_diacritics_and_punctuation():
    assert normalize_name("  João  Cancelo ") == "joao cancelo"
    assert normalize_name("Son Heung-Min") == "son heung min"


def test_exact_dob_and_normalized_name_auto_link():
    left = PlayerIdentity("a", "1", "João Cancelo", date(1994, 5, 27), "Portugal")
    right = PlayerIdentity("b", "99", "Joao Cancelo", date(1994, 5, 27), "Portugal")
    decision = compare_players(left, right)
    assert decision.auto_link is True
    assert decision.method == "deterministic_dob_name"


def test_same_common_name_without_dob_requires_review():
    left = PlayerIdentity("a", "1", "João Pedro", team="Brighton")
    right = PlayerIdentity("b", "2", "Joao Pedro", team="Hull")
    decision = compare_players(left, right)
    assert decision.auto_link is False
    assert decision.method == "review_required"


def test_conflicting_birth_dates_never_link():
    left = PlayerIdentity("a", "1", "Alex Smith", date(1999, 1, 1))
    right = PlayerIdentity("b", "2", "Alex Smith", date(2000, 1, 1))
    decision = compare_players(left, right)
    assert decision.score == 0
    assert decision.auto_link is False
