from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from football_intelligence.events import CanonicalEvent


@dataclass(frozen=True)
class QuarantinedEvent:
    event: CanonicalEvent
    reason: str


@dataclass(frozen=True)
class EventQualityResult:
    accepted: tuple[CanonicalEvent, ...]
    quarantined: tuple[QuarantinedEvent, ...]

    @property
    def reason_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.reason for item in self.quarantined).items()))


def validate_events(events: list[CanonicalEvent]) -> EventQualityResult:
    """Apply source-independent hard invariants before canonical persistence."""
    accepted: list[CanonicalEvent] = []
    quarantined: list[QuarantinedEvent] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        key = (event.provider, event.provider_event_id)
        reason: str | None = None
        if key in seen:
            reason = "DUPLICATE_PROVIDER_EVENT_ID"
        elif not event.provider_match_id:
            reason = "MISSING_MATCH_ID"
        elif not event.provider_team_id:
            reason = "MISSING_TEAM_ID"
        elif event.normalized_x_m is not None and not 0 <= event.normalized_x_m <= 105:
            reason = "START_X_OUT_OF_RANGE"
        elif event.normalized_y_m is not None and not 0 <= event.normalized_y_m <= 68:
            reason = "START_Y_OUT_OF_RANGE"
        elif event.normalized_end_x_m is not None and not 0 <= event.normalized_end_x_m <= 105:
            reason = "END_X_OUT_OF_RANGE"
        elif event.normalized_end_y_m is not None and not 0 <= event.normalized_end_y_m <= 68:
            reason = "END_Y_OUT_OF_RANGE"
        elif event.shot_xg is not None and not 0 <= event.shot_xg <= 1:
            reason = "XG_OUT_OF_RANGE"
        if reason:
            quarantined.append(QuarantinedEvent(event=event, reason=reason))
        else:
            accepted.append(event)
            seen.add(key)
    return EventQualityResult(tuple(accepted), tuple(quarantined))
