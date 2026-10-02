from football_intelligence.search_language import parse_scout_query


def test_scout_query_extracts_constraints_and_traits_for_confirmation():
    parsed = parse_scout_query(
        "Find a pressing winger under 24, under €35m, at least 1200 minutes with dribbling"
    )
    assert parsed.position == "WM"
    assert parsed.maximum_age == 24
    assert parsed.maximum_value_millions == 35
    assert parsed.minimum_minutes == 1200
    assert parsed.traits == ("pressing", "dribbling")


def test_scout_query_does_not_invent_unknown_constraints():
    parsed = parse_scout_query("someone exciting")
    assert parsed.position is None
    assert parsed.unparsed_terms == ("someone exciting",)
