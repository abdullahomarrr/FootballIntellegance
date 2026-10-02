from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0


class CoordinateSystem(StrEnum):
    WYSCOUT_100 = "wyscout_0_100"
    STATSBOMB_120_80 = "statsbomb_120_80"


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


def normalize_point(
    x: float | None,
    y: float | None,
    system: CoordinateSystem,
    *,
    reverse_attack: bool = False,
) -> Point | None:
    if x is None or y is None:
        return None
    max_x, max_y = {
        CoordinateSystem.WYSCOUT_100: (100.0, 100.0),
        CoordinateSystem.STATSBOMB_120_80: (120.0, 80.0),
    }[system]
    if not 0 <= x <= max_x or not 0 <= y <= max_y:
        raise ValueError(f"Coordinate ({x}, {y}) outside {system}")
    x_m = x / max_x * PITCH_LENGTH_M
    y_m = y / max_y * PITCH_WIDTH_M
    if reverse_attack:
        x_m = PITCH_LENGTH_M - x_m
        y_m = PITCH_WIDTH_M - y_m
    return Point(x=round(x_m, 6), y=round(y_m, 6))
