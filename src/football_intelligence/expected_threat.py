from __future__ import annotations

from dataclasses import dataclass

from football_intelligence.events import CanonicalEvent


@dataclass(frozen=True)
class EventThreat:
    provider_event_id: str
    provider_player_id: str | None
    start_value: float
    end_value: float
    xt_added: float


class ExpectedThreatModel:
    """Versioned, transparent location-value baseline on the canonical pitch."""

    version = "xt_location_baseline_v1"

    def __init__(self, columns: int = 12, rows: int = 8) -> None:
        if columns <= 0 or rows <= 0:
            raise ValueError("xT grid dimensions must be positive")
        self.columns = columns
        self.rows = rows

    def value(self, x_m: float, y_m: float) -> float:
        if not 0 <= x_m <= 105 or not 0 <= y_m <= 68:
            raise ValueError("Coordinates must be on a 105x68 metre pitch")
        # A deterministic baseline, not provider xG: value rises toward the goal and
        # through central lanes. It is deliberately versioned for later empirical fitting.
        progress = x_m / 105
        centrality = 1 - abs(y_m - 34) / 34
        return round((progress**3) * (0.65 + 0.35 * centrality), 6)

    def score_event(self, event: CanonicalEvent) -> EventThreat | None:
        if event.event_type.casefold() not in {"pass", "carry"}:
            return None
        coordinates = (
            event.normalized_x_m,
            event.normalized_y_m,
            event.normalized_end_x_m,
            event.normalized_end_y_m,
        )
        if any(value is None for value in coordinates):
            return None
        if event.outcome and event.outcome.casefold() in {"incomplete", "out", "pass offside"}:
            return None
        start_x, start_y, end_x, end_y = coordinates
        assert start_x is not None and start_y is not None
        assert end_x is not None and end_y is not None
        start = self.value(start_x, start_y)
        end = self.value(end_x, end_y)
        return EventThreat(
            provider_event_id=event.provider_event_id,
            provider_player_id=event.provider_player_id,
            start_value=start,
            end_value=end,
            xt_added=round(end - start, 6),
        )

    def player_totals(self, events: list[CanonicalEvent]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for event in events:
            scored = self.score_event(event)
            if scored is not None and scored.provider_player_id is not None:
                totals[scored.provider_player_id] = round(
                    totals.get(scored.provider_player_id, 0) + scored.xt_added, 6
                )
        return totals
