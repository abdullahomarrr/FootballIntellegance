import json

from football_intelligence.display_names import (
    choose_rule_based,
    expand_initial,
    is_grounded,
    llm_batch,
    parse_llm_response,
)

MESSI = "Lionel Andrés Messi Cuccittini"


def test_rule1_statsbomb_nickname_wins() -> None:
    assert choose_rule_based(MESSI, ["Lionel Messi"], ["L. Messi"]) == (
        "Lionel Messi",
        "statsbomb_nickname",
    )


def test_rule2_wyscout_initial_expansion() -> None:
    assert choose_rule_based(MESSI, [], ["L. Messi"]) == ("Lionel Messi", "wyscout_short")
    assert expand_initial("Ngolo Kanté Diarra", "N. Kanté") == "Ngolo Kanté"
    assert expand_initial("Álvaro Borja Morata", "Á. Mo­rata") == "Álvaro Morata"
    assert expand_initial(MESSI, "J. Messi") is None
    assert expand_initial(MESSI, "Jorginho") is None


def test_rule3_short_names_keep_canonical() -> None:
    assert choose_rule_based("Toni Kroos", [], ["T. Kroos"]) == ("Toni Kroos", "canonical")


def test_needs_llm_when_no_rule_applies() -> None:
    assert choose_rule_based(MESSI, [], []) is None


def test_grounding_check() -> None:
    assert is_grounded("Lionel Messi", MESSI)
    assert is_grounded("lionel andres messi", MESSI)
    assert not is_grounded("Leo Messi", MESSI)
    assert not is_grounded("", MESSI)
    assert not is_grounded(MESSI + " Jr", MESSI)
    assert is_grounded("Leo", MESSI, mononyms=["Leo"])


def test_parse_and_batch_with_fake_caller() -> None:
    reply = "```json\n" + json.dumps([{"id": 1, "display_name": "Lionel Messi"}]) + "\n```"
    assert parse_llm_response(reply) == {1: "Lionel Messi"}
    calls: list[str] = []

    def flaky(system: str, user: str) -> str:
        calls.append(user)
        if len(calls) < 3:
            return "not json"
        return reply

    batch = [{"player_id": 1, "canonical_name": MESSI, "nationality": "ARG"}]
    assert llm_batch(flaky, batch, sleep=lambda _s: None) == {1: "Lionel Messi"}
    assert len(calls) == 3
    assert llm_batch(lambda _s, _u: "nope", batch, sleep=lambda _s: None) == {}
