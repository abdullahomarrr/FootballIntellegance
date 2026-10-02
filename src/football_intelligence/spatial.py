from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from football_intelligence.events import CanonicalEvent


class SpatialCell(BaseModel):
    x_bin: int
    y_bin: int
    events: int


class PlayerSpatialProfile(BaseModel):
    provider_player_id: str
    match_id: str
    event_count: int
    located_event_count: int
    mean_x_m: float | None
    mean_y_m: float | None
    event_type_counts: dict[str, int]
    heatmap: list[SpatialCell]
    grid_columns: int
    grid_rows: int


def build_spatial_profile(
    events: list[CanonicalEvent],
    provider_player_id: str,
    *,
    grid_columns: int = 12,
    grid_rows: int = 8,
) -> PlayerSpatialProfile:
    if grid_columns <= 0 or grid_rows <= 0:
        raise ValueError("Heatmap grid dimensions must be positive")
    selected = [event for event in events if event.provider_player_id == provider_player_id]
    located = [
        event
        for event in selected
        if event.normalized_x_m is not None and event.normalized_y_m is not None
    ]
    cells: Counter[tuple[int, int]] = Counter()
    for event in located:
        assert event.normalized_x_m is not None and event.normalized_y_m is not None
        x_bin = min(int(event.normalized_x_m / 105 * grid_columns), grid_columns - 1)
        y_bin = min(int(event.normalized_y_m / 68 * grid_rows), grid_rows - 1)
        cells[(x_bin, y_bin)] += 1
    match_ids = {event.provider_match_id for event in selected}
    return PlayerSpatialProfile(
        provider_player_id=provider_player_id,
        match_id=next(iter(match_ids), ""),
        event_count=len(selected),
        located_event_count=len(located),
        mean_x_m=(
            round(sum(event.normalized_x_m or 0 for event in located) / len(located), 3)
            if located
            else None
        ),
        mean_y_m=(
            round(sum(event.normalized_y_m or 0 for event in located) / len(located), 3)
            if located
            else None
        ),
        event_type_counts=dict(sorted(Counter(event.event_type for event in selected).items())),
        heatmap=[
            SpatialCell(x_bin=x_bin, y_bin=y_bin, events=count)
            for (x_bin, y_bin), count in sorted(cells.items())
        ],
        grid_columns=grid_columns,
        grid_rows=grid_rows,
    )


def load_canonical_jsonl(path: Path) -> list[CanonicalEvent]:
    with path.open(encoding="utf-8") as stream:
        return [CanonicalEvent.model_validate(json.loads(line)) for line in stream if line.strip()]
