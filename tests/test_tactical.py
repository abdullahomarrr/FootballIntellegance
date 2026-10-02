from football_intelligence.tactical import classify_archetype, tactical_fit, team_style_profile
from tests.test_spatial import event


def test_team_style_is_built_from_observed_events():
    first = event("1", "p1", 10, 20).model_copy(update={"normalized_end_x_m": 30})
    pressure = event("2", "p2", 20, 20).model_copy(update={"event_type": "Pressure"})
    profile = team_style_profile([first, pressure], "t1")
    assert profile.pass_share == 0.5
    assert profile.pressure_share == 0.5
    assert profile.vertical_progression_m == 20


def test_tactical_fit_reports_missing_and_sample_confidence():
    fit = tactical_fit({"press": 2, "carry": None}, {"press": 2, "carry": 1}, player_minutes=300)
    assert fit.score == 100
    assert fit.confidence == "LOW"
    assert fit.missing_dimensions == ("carry",)


def test_archetype_is_explainable_and_missing_safe():
    label, missing = classify_archetype({"pressures": 9, "carries": 2, "shots": None})
    assert label == "PRESSING_SPECIALIST"
    assert missing == ("shots",)
    assert classify_archetype({"shots": None})[0] == "INSUFFICIENT_DATA"


def _rows(team_value: float, player_value: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for player_id in range(1, 8):
        for metric in ("pressures_per_90", "recoveries_per_90", "progressive_passes_per_90"):
            high = metric != "progressive_passes_per_90"
            rows.append(
                {
                    "player_id": player_id,
                    "minutes_played": 2000,
                    "metric_name": metric,
                    "percentile": team_value if high else 30,
                    "is_target": player_id == 1,
                }
            )
    for row in rows:
        if row["is_target"] and row["metric_name"] == "progressive_passes_per_90":
            row["percentile"] = player_value
    return rows


def test_team_style_identifies_the_dominant_axis_and_what_the_player_adds():
    from football_intelligence.tactical import build_tactical_context

    context = build_tactical_context(_rows(team_value=80, player_value=90))
    assert context is not None
    assert context.style == "Press-and-win"
    assert context.style_strength == "DISTINCT"
    assert any("Progression" in item for item in context.adds)
    assert context.team_player_count == 7


def test_team_context_refuses_tiny_squads():
    from football_intelligence.tactical import build_tactical_context

    assert build_tactical_context(_rows(80, 90)[:6]) is None


def test_role_fit_weights_priorities_and_reports_drivers_and_gaps():
    from football_intelligence.tactical import role_fit

    result = role_fit(
        {"pressures_per_90": 90, "recoveries_per_90": 70, "xg_per_90": 20},
        {"pressures_per_90": 3, "recoveries_per_90": 1, "xg_per_90": 1, "box_entries_per_90": 0},
    )
    assert result is not None
    assert round(result.score, 1) == 72.0
    assert result.coverage == 1.0
    assert result.drivers[0][0] == "pressures_per_90"
    assert result.gaps == (("xg_per_90", 20),)


def test_role_fit_refuses_roles_the_evidence_cannot_cover():
    from football_intelligence.tactical import role_fit

    assert role_fit({"xg_per_90": 90}, {"pressures_per_90": 3, "xg_per_90": 1}) is None
    assert role_fit({}, {"xg_per_90": 1}) is None
