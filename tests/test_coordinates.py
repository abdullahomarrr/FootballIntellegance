import pytest

from football_intelligence.coordinates import CoordinateSystem, Point, normalize_point


@pytest.mark.parametrize(
    ("system", "x", "y", "expected"),
    [
        (CoordinateSystem.WYSCOUT_100, 0, 0, Point(0, 0)),
        (CoordinateSystem.WYSCOUT_100, 100, 100, Point(105, 68)),
        (CoordinateSystem.STATSBOMB_120_80, 60, 40, Point(52.5, 34)),
    ],
)
def test_normalize_boundaries(system, x, y, expected):
    assert normalize_point(x, y, system) == expected


def test_reverse_attack_flips_both_axes():
    assert normalize_point(20, 25, CoordinateSystem.WYSCOUT_100, reverse_attack=True) == Point(
        84, 51
    )


def test_missing_coordinate_remains_missing():
    assert normalize_point(None, 10, CoordinateSystem.WYSCOUT_100) is None


def test_out_of_bounds_is_rejected():
    with pytest.raises(ValueError, match="outside"):
        normalize_point(121, 40, CoordinateSystem.STATSBOMB_120_80)
