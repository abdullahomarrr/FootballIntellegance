from football_intelligence.quality import validate_events
from tests.test_spatial import event


def test_quality_accepts_valid_and_quarantines_duplicates_and_bad_coordinates():
    valid = event("1", "p1", 10, 20)
    duplicate = valid.model_copy()
    bad = event("2", "p1", 10, 20).model_copy(update={"normalized_x_m": 106})
    result = validate_events([valid, duplicate, bad])
    assert result.accepted == (valid,)
    assert result.reason_counts == {
        "DUPLICATE_PROVIDER_EVENT_ID": 1,
        "START_X_OUT_OF_RANGE": 1,
    }
