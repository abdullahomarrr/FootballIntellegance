"""Estimate a club's likely starting XI and lay it out on a pitch.

FotMob squad pages carry no official team sheet, so the XI is estimated: the keeper and ten
outfield players with the most minutes this season (falling back to match rating, then market
value), arranged in lines by position group, with each line ordered left to right from the
position codes FotMob lists for the player. It describes who has played most, not who will start.
"""

from __future__ import annotations

from typing import Any

MIN_LINE = {"DF": 3, "MD": 2, "FW": 1}
MAX_LINE = {"DF": 4, "MD": 5, "FW": 3}
LINE_Y = {"GK": 90.0, "DF": 70.0, "MD": 45.0, "FW": 18.0}


def _score(player: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(player.get("minutes") or 0),
        float(player.get("rating") or 0),
        float(player.get("market_value_eur") or 0),
    )


def _side(player: dict[str, Any]) -> int:
    """0 = left, 1 = centre, 2 = right, from the first position code FotMob lists."""
    codes = str(player.get("position_codes") or "").split(",")
    first = codes[0].strip().upper() if codes and codes[0].strip() else ""
    if not first or first in {"GK", "ST", "CF", "CM", "DM", "AM", "CB"}:
        return 1
    if first.startswith("L") or first.endswith("L"):
        return 0
    if first.startswith("R") or first.endswith("R"):
        return 2
    return 1


def _pick_outfield(outfield: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(outfield, key=_score, reverse=True)
    chosen = ranked[:10]
    rest = ranked[10:]

    def count(group: str) -> int:
        return sum(1 for player in chosen if player["position_group"] == group)

    # Make the shape playable: pull in the best available player of a short line and drop the
    # weakest player from a line that can spare one.
    for group, minimum in MIN_LINE.items():
        while count(group) < minimum:
            candidate = next((p for p in rest if p["position_group"] == group), None)
            if candidate is None:
                break
            donors = [
                p
                for p in chosen
                if count(p["position_group"]) > MIN_LINE.get(p["position_group"], 0)
                and p["position_group"] != group
            ]
            if not donors:
                break
            chosen.remove(min(donors, key=_score))
            chosen.append(candidate)
            rest.remove(candidate)
    for group, maximum in MAX_LINE.items():
        while count(group) > maximum:
            chosen.remove(min((p for p in chosen if p["position_group"] == group), key=_score))
            fill = next(
                (
                    p
                    for p in rest
                    if p["position_group"] != group
                    and count(p["position_group"]) < MAX_LINE[p["position_group"]]
                ),
                None,
            )
            if fill is None:
                break
            chosen.append(fill)
            rest.remove(fill)
    return chosen


def build_lineup(players: list[dict[str, Any]]) -> dict[str, Any]:
    """{formation, starters: [{player_id, x, y}], bench: [player_id]} for one squad."""
    keepers = sorted((p for p in players if p["position_group"] == "GK"), key=_score, reverse=True)
    outfield = [p for p in players if p["position_group"] in MIN_LINE]
    starters: list[dict[str, Any]] = []
    chosen_ids: set[int] = set()
    if keepers:
        keeper = keepers[0]
        starters.append({"player_id": keeper["player_id"], "x": 50.0, "y": LINE_Y["GK"]})
        chosen_ids.add(int(keeper["player_id"]))
    lines: dict[str, list[dict[str, Any]]] = {"DF": [], "MD": [], "FW": []}
    for player in _pick_outfield(outfield):
        lines[player["position_group"]].append(player)
    for group, line in lines.items():
        ordered = sorted(line, key=lambda p: (_side(p), -_score(p)[0]))
        for index, player in enumerate(ordered):
            starters.append(
                {
                    "player_id": player["player_id"],
                    "x": round((index + 1) / (len(ordered) + 1) * 100, 1),
                    "y": LINE_Y[group],
                }
            )
            chosen_ids.add(int(player["player_id"]))
    bench = [
        int(p["player_id"])
        for p in sorted(players, key=_score, reverse=True)
        if int(p["player_id"]) not in chosen_ids
    ]
    formation = "-".join(str(len(lines[group])) for group in ("DF", "MD", "FW"))
    return {"formation": formation, "starters": starters, "bench": bench}
