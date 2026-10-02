from football_intelligence.model_registry import CoverageFlags, select_similarity_model


def test_model_hierarchy_chooses_deepest_compatible_model():
    assert (
        select_similarity_model(CoverageFlags(basic=True, event_spatial=True)).model_version
        == "SIMILARITY_SPATIAL_V1"
    )
    assert (
        select_similarity_model(CoverageFlags(basic=True, advanced_match=True)).model_version
        == "SIMILARITY_ADVANCED_V1"
    )
    assert select_similarity_model(CoverageFlags(basic=True)).model_version == "SIMILARITY_BASIC_V1"


def test_model_hierarchy_fails_closed_without_basic_features():
    result = select_similarity_model(CoverageFlags(event_spatial=True))
    assert result.status == "INSUFFICIENT_FEATURE_COVERAGE"
    assert result.missing_requirements == ("basic",)
