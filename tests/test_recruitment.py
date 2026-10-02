from football_intelligence.recruitment import (
    Candidate,
    RecruitmentConstraints,
    rank_candidates,
)


def test_recruitment_applies_hard_filters_then_ranks():
    candidates = [
        Candidate(1, "Close", 22, 10, 1200, {"passing": 1, "carrying": 1}),
        Candidate(2, "Too old", 31, 5, 2000, {"passing": 1, "carrying": 1}),
        Candidate(3, "Low sample", 20, 3, 200, {"passing": 1, "carrying": 1}),
        Candidate(4, "Different", 21, 8, 1500, {"passing": -1, "carrying": 0}),
    ]
    ranked = rank_candidates(
        {"passing": 1, "carrying": 1},
        candidates,
        RecruitmentConstraints(maximum_age=25, maximum_value=12, minimum_minutes=900),
    )
    assert [item.candidate.name for item in ranked] == ["Close", "Different"]


def test_recruitment_excludes_incompatible_feature_profiles():
    ranked = rank_candidates(
        {"passing": None},
        [Candidate(1, "No overlap", 20, None, 1000, {"passing": None})],
        RecruitmentConstraints(),
    )
    assert ranked == []
