"""Load the Reep player ID crosswalk (CC0, derived from Wikidata) into the warehouse.

Reep maps one person across provider ID systems. Here it is used only to link identities
(Transfermarkt, Wyscout, Opta numeric); it carries no statistics.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any


def _birth(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def read_crosswalk(path: Path) -> list[tuple[Any, ...]]:
    csv.field_size_limit(10**9)
    rows: list[tuple[Any, ...]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["type"] != "player":
                continue
            opta, wyscout = row["key_opta_numeric"], row["key_wyscout"]
            if not (opta or wyscout):
                continue
            tm = row["key_transfermarkt"]
            rows.append(
                (
                    row["reep_id"],
                    opta or None,
                    int(tm) if tm.isdigit() else None,
                    wyscout or None,
                    row["name"] or None,
                    _birth(row["date_of_birth"]),
                )
            )
    return rows


def load_crosswalk(connection: Any, path: Path) -> int:
    rows = read_crosswalk(path)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM reep_crosswalk")
        cursor.executemany(
            """INSERT INTO reep_crosswalk
               (reep_id, opta_numeric, tm_player_id, wyscout_id, name, date_of_birth)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            rows,
        )
    connection.commit()
    return len(rows)
