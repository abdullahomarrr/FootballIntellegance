from football_intelligence.scout_report import build_scout_report, complete_metric_family


def test_scout_report_claims_are_metric_backed_and_caveated():
    report = build_scout_report(
        player_name="Example Player",
        percentiles={"passing": 91, "pressing": 22, "aerial": None},
        minutes=430,
        coverage_level="BASIC",
    )
    assert report.strengths[0].evidence_metrics == ("passing",)
    assert report.risks[0].evidence_metrics == ("pressing",)
    assert any("430 minutes" in caveat for caveat in report.caveats)
    assert any("Spatial" in caveat for caveat in report.caveats)
    assert "not a scouting verdict" in report.summary


def test_scout_report_uses_a_separate_goalkeeper_archetype_family():
    report = build_scout_report(
        player_name="Example Keeper",
        percentiles={
            "goalkeeper_saves_per_90": 82,
            "goals_conceded_per_90": 91,
            "claims_and_punches_per_90": 43,
            "sweeper_actions_per_90": 30,
        },
        minutes=2400,
        coverage_level="EVENT_ADVANCED",
        position_group="GK",
    )
    assert report.archetype == "Shot-stopper"
    assert set(report.archetype_evidence) <= {
        "goalkeeper_saves_per_90",
        "goals_conceded_per_90",
        "claims_and_punches_per_90",
        "sweeper_actions_per_90",
    }
    assert all(name.startswith(("goal", "claims", "sweeper")) for name in report.archetype_evidence)


def test_report_discloses_expected_provider_metrics_that_are_unavailable():
    percentiles = complete_metric_family({"xg_per_90": 82}, "FW")
    report = build_scout_report(
        player_name="Example Forward",
        percentiles=percentiles,
        minutes=1800,
        coverage_level="EVENT_ADVANCED",
        position_group="FW",
    )

    assert len(percentiles) == 15
    assert "Pass completion" in report.caveats[0]
    assert "Expected goals" not in report.caveats[0]
    assert not any("Spatial" in caveat for caveat in report.caveats)


def test_forward_archetype_reflects_finishing_and_names_a_secondary_profile():
    report = build_scout_report(
        player_name="Example Forward",
        percentiles={
            "xg_per_90": 99,
            "average_shot_xg": 90,
            "box_entries_per_90": 74,
            "successful_dribbles_per_90": 85,
            "progressive_carries_per_90": 78,
            "xt_added_per_90": 80,
            "pass_completion_pct": 40,
            "pressured_pass_completion_pct": 40,
            "progressive_passes_per_90": 45,
            "passes_into_final_third_per_90": 50,
            "pressures_per_90": 20,
            "recoveries_per_90": 25,
            "defensive_duels_per_90": 30,
        },
        minutes=2400,
        coverage_level="EVENT_ADVANCED",
        position_group="FW",
    )
    assert report.archetype == "Penalty-area goal threat"
    assert report.secondary_archetype == "Dribbling ball-carrier"
    assert report.archetype_clarity == "CLEAR"
    assert report.profile_fits[0][0] == report.archetype
    assert "99th" in report.summary


def test_archetype_catalogues_are_position_specific():
    defender = build_scout_report(
        player_name="Example Defender",
        percentiles={
            "defensive_duels_per_90": 92,
            "defensive_actions_per_90": 88,
            "pressures_per_90": 80,
            "progressive_passes_per_90": 30,
            "pass_completion_pct": 45,
        },
        minutes=2000,
        coverage_level="EVENT_ADVANCED",
        position_group="DF",
    )
    assert defender.archetype == "Aggressive stopper"
    assert all(name != "Penalty-area goal threat" for name, _ in defender.profile_fits)


def test_weak_profiles_are_flagged_instead_of_labelled_confidently():
    report = build_scout_report(
        player_name="Example Midfielder",
        percentiles={"progressive_passes_per_90": 40, "pass_completion_pct": 45,
                     "recoveries_per_90": 35, "defensive_duels_per_90": 42,
                     "defensive_actions_per_90": 38, "pressures_per_90": 30},
        minutes=1500,
        coverage_level="EVENT_ADVANCED",
        position_group="MD",
    )
    assert report.archetype_clarity == "WEAK"
    assert any("No archetype stands out" in caveat for caveat in report.caveats)


def test_missing_provider_metrics_limit_the_archetype_instead_of_overclaiming():
    report = build_scout_report(
        player_name="Example Midfielder",
        percentiles={
            "progressive_passes_per_90": 88,
            "passes_into_final_third_per_90": 85,
            "pass_completion_pct": 90,
        },
        minutes=2600,
        coverage_level="EVENT_ADVANCED",
        position_group="MD",
    )
    assert report.archetype == "Deep-lying playmaker"
    assert report.archetype_clarity == "LIMITED"
    assert any("could not be assessed" in caveat for caveat in report.caveats)
