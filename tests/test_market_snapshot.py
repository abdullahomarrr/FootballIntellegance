from datetime import date

from football_intelligence import market_snapshot as ms
from football_intelligence.market_snapshot import (
    OurPlayer,
    SnapshotPlayer,
    country_key,
    fold,
    match_players,
    name_variants,
    propagate_person_links,
)


def _snapshot(*players: SnapshotPlayer):
    index: dict[str, set[int]] = {}
    for player in players:
        for variant in name_variants(player.name):
            index.setdefault(variant, set()).add(player.tm_player_id)
    return {p.tm_player_id: p for p in players}, index


def _tm(tm_id, name, birth=None, country="Spain", position="FW"):
    return SnapshotPlayer(tm_id, name, birth, country, None, None, position)


def test_names_are_folded_and_expanded_to_common_variants():
    assert fold("Kylian Mbappé Lottin") == "kylian mbappe lottin"
    assert fold("N'Golo Kanté") == "ngolo kante"
    variants = name_variants("Lionel Andrés Messi Cuccittini")
    assert {"lionel messi", "lionel andres messi cuccittini", "lionel cuccittini"} <= variants
    assert country_key("Côte d'Ivoire") == "ivory coast"


def test_birth_date_match_is_exact_and_beats_name_only():
    snapshot, index = _snapshot(
        _tm(1, "Lionel Messi", date(1987, 6, 24)), _tm(2, "Lionel Messi", date(2001, 1, 1))
    )
    names = ("Lionel Andrés Messi Cuccittini", "Lionel Messi")
    ours = [OurPlayer(10, names, date(1987, 6, 24), ())]
    matches, _ = match_players(ours, snapshot, index)
    assert matches == {10: (1, ms.BASIS_NAME_DOB)}


def test_birth_date_mismatch_is_never_linked():
    snapshot, index = _snapshot(_tm(1, "Lionel Messi", date(1987, 6, 24)))
    ours = [OurPlayer(10, ("Lionel Messi",), date(1990, 1, 1), ("Spain",))]
    matches, stats = match_players(ours, snapshot, index)
    assert matches == {} and stats["dob_mismatch"] == 1


def test_nationality_match_needs_a_unique_candidate_and_agreeing_position():
    snapshot, index = _snapshot(
        _tm(1, "Pedro Lopez", country="Spain", position="Attack"),
        _tm(2, "Pedro Lopez", country="Spain", position="Defender"),
        _tm(3, "Pedro Lopez", country="Chile", position="Attack"),
    )
    snapshot[1] = SnapshotPlayer(1, "Pedro Lopez", None, "Spain", None, None, "FW")
    snapshot[2] = SnapshotPlayer(2, "Pedro Lopez", None, "Spain", None, None, "DF")
    forward = OurPlayer(10, ("Pedro Lopez",), None, ("Spain",), "FW")
    matches, _ = match_players([forward], snapshot, index)
    assert matches == {10: (1, ms.BASIS_NAME_NATIONALITY)}  # the Spanish defender is excluded
    unknown_position = OurPlayer(11, ("Pedro Lopez",), None, ("Spain",), None)
    matches, stats = match_players([unknown_position], snapshot, index)
    assert matches == {} and stats["ambiguous"] == 1


def test_three_letter_codes_are_not_used_as_nationality_evidence():
    snapshot, index = _snapshot(_tm(1, "Sam Jones", country="England"))
    ours = [OurPlayer(10, ("Sam Jones",), None, ("ENG",))]
    matches, stats = match_players(ours, snapshot, index)
    assert matches == {} and stats["nationality_mismatch"] == 1


def test_other_provider_record_inherits_the_link_and_conflicts_are_dropped():
    matches = {1: (100, ms.BASIS_NAME_DOB)}
    linked, conflicts = propagate_person_links(matches, {1: 1, 2: 1})
    assert linked[2] == (100, ms.BASIS_PERSON) and conflicts == 0
    clash = {1: (100, ms.BASIS_NAME_DOB), 2: (200, ms.BASIS_NAME_NATIONALITY)}
    linked, conflicts = propagate_person_links(clash, {1: 1, 2: 1})
    assert linked == {} and conflicts == 1


def test_market_endpoint_labels_the_source_as_frozen_third_party(monkeypatch):
    from fastapi.testclient import TestClient

    from football_intelligence.api import app

    monkeypatch.setattr(
        "football_intelligence.api.player_market",
        lambda player_id: {
            "market_values": [{"data_as_of": "2026-06-12"}],
            "transfers": [],
            "contract": None,
            "link": {"match_basis": "NAME_AND_BIRTH_DATE"},
        },
    )
    meta = TestClient(app).get("/players/1/market").json()["meta"]
    assert "frozen" in meta["source_label"] and meta["link_basis"] == "NAME_AND_BIRTH_DATE"
    assert meta["market_value_is_transfer_fee"] is False


def test_values_are_attached_to_peer_rows_when_linked(monkeypatch):
    from football_intelligence import api

    monkeypatch.setattr(
        api,
        "values_at_seasons",
        lambda pairs: {(1, "2017/18"): {"amount": 5_000_000, "valuation_date": date(2018, 5, 1)}},
    )
    rows = api._with_values(
        [
            {"player_id": 1, "season_label": "2017/18"},
            {"player_id": 2, "season_label": "2017/18"},
        ]
    )
    assert rows[0]["market_value_eur"] == 5_000_000.0
    assert rows[1]["market_value_eur"] is None


def test_an_exact_id_link_outranks_a_name_based_link_for_the_whole_person():
    matches = {1: (100, ms.BASIS_ID), 2: (200, ms.BASIS_NAME_NATIONALITY)}
    linked, conflicts = propagate_person_links(matches, {1: 1, 2: 1})
    assert linked == {1: (100, ms.BASIS_ID), 2: (100, ms.BASIS_PERSON)} and conflicts == 0
