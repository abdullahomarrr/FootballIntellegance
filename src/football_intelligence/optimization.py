from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SquadCandidate:
    player_id: int
    name: str
    positions: tuple[str, ...]
    cost: float
    fit_score: float


@dataclass(frozen=True, slots=True)
class SquadSelection:
    assignments: tuple[tuple[str, SquadCandidate], ...]
    total_cost: float
    total_fit: float


def optimize_squad(
    needs: tuple[str, ...], candidates: list[SquadCandidate], budget: float
) -> SquadSelection | None:
    if budget < 0:
        raise ValueError("Budget cannot be negative")
    best: SquadSelection | None = None

    def search(
        index: int,
        used: frozenset[int],
        assignments: tuple[tuple[str, SquadCandidate], ...],
        cost: float,
        fit: float,
    ) -> None:
        nonlocal best
        if cost > budget:
            return
        if index == len(needs):
            selection = SquadSelection(assignments, round(cost, 2), round(fit, 2))
            if best is None or (selection.total_fit, -selection.total_cost) > (
                best.total_fit,
                -best.total_cost,
            ):
                best = selection
            return
        need = needs[index]
        for candidate in candidates:
            if candidate.player_id in used or need not in candidate.positions:
                continue
            search(
                index + 1,
                used | {candidate.player_id},
                (*assignments, (need, candidate)),
                cost + candidate.cost,
                fit + candidate.fit_score,
            )

    search(0, frozenset(), (), 0.0, 0.0)
    return best
