"""Load the frozen Transfermarkt-derived snapshot and link it to our players.

The snapshot is third-party, derived and frozen (valuations end 2026-06-12). Nothing here
scrapes anything: it reads three audited CSV files already on disk. Matching is conservative
and tiered; anything ambiguous stays unlinked.
"""

from __future__ import annotations

import csv
import gzip
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROVIDER = "transfermarkt_snapshot"
SNAPSHOT_DATE = date(2026, 7, 6)
VALUATIONS_AS_OF = datetime(2026, 6, 12, 23, 59, tzinfo=None)

BASIS_NAME_DOB = "NAME_AND_BIRTH_DATE"
BASIS_NAME_NATIONALITY = "NAME_AND_NATIONALITY"
BASIS_PERSON = "SAME_PERSON_OTHER_PROVIDER"
BASIS_ID = "ID_CROSSWALK"

# StatsBomb country names differ from Transfermarkt in a few places.
COUNTRY_ALIASES = {
    "cote divoire": "ivory coast",
    "czechia": "czech republic",
    "korea republic": "south korea",
    "republic of ireland": "ireland",
    "united states": "united states",
    "usa": "united states",
    "china pr": "china",
}


def fold(text: str | None) -> str:
    base = unicodedata.normalize("NFKD", text or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = base.replace("­", "").replace("ø", "o").replace("ß", "ss").replace("ł", "l")
    return re.sub(r"[^a-z0-9 ]+", "", base.lower().replace("-", " ").replace("'", "")).strip()


def country_key(value: str | None) -> str:
    key = fold(value)
    return COUNTRY_ALIASES.get(key, key)


def name_variants(*names: str | None) -> set[str]:
    """Normalised ways a player's name can be written (full, first+last, first+second surname)."""
    variants: set[str] = set()
    for name in names:
        key = fold(name)
        if not key:
            continue
        variants.add(key)
        tokens = key.split()
        if len(tokens) >= 3:
            variants.add(f"{tokens[0]} {tokens[-1]}")
            variants.add(f"{tokens[0]} {tokens[-2]}")
    return {v for v in variants if len(v.split()) >= 2 or len(v) >= 6}


@dataclass(frozen=True)
class SnapshotPlayer:
    tm_player_id: int
    name: str
    birth_date: date | None
    citizenship: str
    contract_expires: date | None
    current_club: str | None
    position_group: str | None = None


POSITION_GROUPS = {"goalkeeper": "GK", "defender": "DF", "midfield": "MD", "attack": "FW"}


def _rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip()[:10]).date()
    except ValueError:
        return None


def read_snapshot_players(directory: Path) -> tuple[list[SnapshotPlayer], dict[str, set[int]]]:
    players: list[SnapshotPlayer] = []
    index: dict[str, set[int]] = defaultdict(set)
    for row in _rows(directory / "players.csv.gz"):
        player = SnapshotPlayer(
            tm_player_id=int(row["player_id"]),
            name=row["name"],
            birth_date=_parse_date(row["date_of_birth"]),
            citizenship=row["country_of_citizenship"],
            contract_expires=_parse_date(row["contract_expiration_date"]),
            current_club=row["current_club_name"] or None,
            position_group=POSITION_GROUPS.get(row["position"].strip().lower()),
        )
        players.append(player)
        for variant in name_variants(row["name"], f"{row['first_name']} {row['last_name']}"):
            index[variant].add(player.tm_player_id)
    return players, index


@dataclass(frozen=True)
class OurPlayer:
    player_id: int
    names: tuple[str, ...]
    birth_date: date | None
    nationalities: tuple[str, ...]
    position_group: str | None = None


def match_players(
    ours: list[OurPlayer],
    snapshot: dict[int, SnapshotPlayer],
    index: dict[str, set[int]],
) -> tuple[dict[int, tuple[int, str]], dict[str, int]]:
    """Return {player_id: (tm_player_id, basis)} plus diagnostics."""
    matches: dict[int, tuple[int, str]] = {}
    stats = {"no_candidate": 0, "ambiguous": 0, "dob_mismatch": 0, "nationality_mismatch": 0}
    for player in ours:
        candidates: set[int] = set()
        for variant in name_variants(*player.names):
            candidates |= index.get(variant, set())
        if not candidates:
            stats["no_candidate"] += 1
            continue
        if player.birth_date is not None:
            same_birth = {c for c in candidates if snapshot[c].birth_date == player.birth_date}
            if len(same_birth) == 1:
                matches[player.player_id] = (next(iter(same_birth)), BASIS_NAME_DOB)
            elif len(same_birth) > 1:
                stats["ambiguous"] += 1
            else:
                stats["dob_mismatch"] += 1
            continue
        wanted = {country_key(n) for n in player.nationalities if len(n) > 3}
        same_country = {
            c
            for c in candidates
            if country_key(snapshot[c].citizenship) in wanted
            # Without a birth date the link is weaker, so the position must also agree.
            and (
                player.position_group is None
                or snapshot[c].position_group is None
                or snapshot[c].position_group == player.position_group
            )
        }
        if len(same_country) == 1:
            matches[player.player_id] = (next(iter(same_country)), BASIS_NAME_NATIONALITY)
        elif len(same_country) > 1:
            stats["ambiguous"] += 1
        else:
            stats["nationality_mismatch"] += 1
    return matches, stats


def propagate_person_links(
    matches: dict[int, tuple[int, str]], person_of: dict[int, int]
) -> tuple[dict[int, tuple[int, str]], int]:
    """Give a person's other provider record the same snapshot link; drop conflicts."""
    by_person: dict[int, dict[int, tuple[int, str]]] = defaultdict(dict)
    for player_id, person_id in person_of.items():
        by_person[person_id][player_id] = matches.get(player_id, (0, ""))
    result = dict(matches)
    conflicts = 0
    for members in by_person.values():
        exact = {tm for tm, basis in members.values() if tm and basis == BASIS_ID}
        if len(exact) == 1:  # an exact ID link outranks any name-based link of the same person
            tm = next(iter(exact))
            for player_id, (_, basis) in members.items():
                result[player_id] = (tm, BASIS_ID if basis == BASIS_ID else BASIS_PERSON)
            continue
        linked = {tm for tm, _ in members.values() if tm}
        if len(linked) > 1:
            conflicts += 1
            for player_id in members:
                result.pop(player_id, None)
        elif len(linked) == 1:
            tm = next(iter(linked))
            for player_id, (current, _) in members.items():
                if not current:
                    result[player_id] = (tm, BASIS_PERSON)
    return result, conflicts


def _our_players(connection: Any) -> list[OurPlayer]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.player_id, p.canonical_name, p.display_name, p.birth_date,
                   p.nationality_codes,
                   coalesce(array_agg(DISTINCT a.alias) FILTER (WHERE a.alias IS NOT NULL), '{}'),
                   (SELECT mode() WITHIN GROUP (ORDER BY i.position_group)
                    FROM analytics.mart_player_season_intelligence i
                    WHERE i.player_id = p.player_id AND i.position_group IS NOT NULL)
            FROM dim_player p
            LEFT JOIN player_alias a ON a.player_id = p.player_id
            GROUP BY p.player_id
            """
        )
        players = []
        for row in cursor.fetchall():
            player_id, canonical, display, birth, nationalities, aliases, position = row
            names = tuple(n for n in [canonical, display, *aliases] if n)
            players.append(
                OurPlayer(player_id, names, birth, tuple(nationalities or ()), position)
            )
        return players


def build_report(connection: Any, matches: dict[int, tuple[int, str]]) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(DISTINCT player_id) FILTER (WHERE minutes_played >= 900),
                   count(DISTINCT player_id)
            FROM analytics.mart_player_season_intelligence
            """
        )
        qualified_total, event_total = cursor.fetchone()
        cursor.execute(
            """
            SELECT DISTINCT player_id FROM analytics.mart_player_season_intelligence
            WHERE minutes_played >= 900
            """
        )
        qualified = {row[0] for row in cursor.fetchall()}
    basis_counts: dict[str, int] = defaultdict(int)
    for _, basis in matches.values():
        basis_counts[basis] += 1
    matched_qualified = len(qualified & set(matches))
    return {
        "linked_players": len(matches),
        "by_basis": dict(basis_counts),
        "qualified_players": qualified_total,
        "qualified_linked": matched_qualified,
        "qualified_match_rate": round(matched_qualified / qualified_total, 3)
        if qualified_total
        else None,
        "players_with_events": event_total,
    }


def load_snapshot(connection: Any, directory: Path, *, write: bool = True) -> dict[str, Any]:
    snapshot_players, index = read_snapshot_players(directory)
    snapshot = {p.tm_player_id: p for p in snapshot_players}
    ours = _our_players(connection)
    matches, stats = match_players(ours, snapshot, index)
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT bridge.player_id, crosswalk.tm_player_id
               FROM bridge_player_provider bridge
               JOIN reep_crosswalk crosswalk ON crosswalk.wyscout_id = bridge.provider_player_id
               WHERE bridge.provider = 'wyscout_open' AND bridge.valid_to IS NULL
                 AND crosswalk.tm_player_id IS NOT NULL"""
        )
        id_pairs = {int(pid): int(tm) for pid, tm in cursor.fetchall() if int(tm) in snapshot}
    corrected = sum(1 for pid, tm in id_pairs.items() if matches.get(pid, (None,))[0] != tm)
    for pid, tm in id_pairs.items():
        matches[pid] = (tm, BASIS_ID)
    with connection.cursor() as cursor:
        cursor.execute("SELECT player_id, person_id FROM player_person")
        person_of = {int(a): int(b) for a, b in cursor.fetchall()}
    matches, conflicts = propagate_person_links(matches, person_of)
    report: dict[str, Any] = {
        "diagnostics": {
            **stats,
            "person_conflicts": conflicts,
            "id_crosswalk_links": len(id_pairs),
            "id_crosswalk_changed_or_added": corrected,
        }
    }
    report.update(build_report(connection, matches))
    if not write:
        return report

    # Facts are stored once per person (the lowest identity), so a profile that reads both
    # provider records never shows a value twice.
    owner = {pid: person_of.get(pid, pid) for pid in matches}
    fact_owner_of_tm: dict[int, int] = {}
    for pid, (tm, _) in matches.items():
        fact_owner_of_tm.setdefault(tm, min(owner[pid], pid))
    tm_ids = set(fact_owner_of_tm)
    uri_values = f"{PROVIDER}:player_valuations.csv.gz"
    uri_transfers = f"{PROVIDER}:transfers.csv.gz"
    uri_players = f"{PROVIDER}:players.csv.gz"

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM bridge_player_transfermarkt")
        cursor.executemany(
            """INSERT INTO bridge_player_transfermarkt
               (player_id, tm_player_id, match_basis, tm_name) VALUES (%s, %s, %s, %s)""",
            [(pid, tm, basis, snapshot[tm].name) for pid, (tm, basis) in matches.items()],
        )
        cursor.execute("DELETE FROM fact_player_market_value WHERE provider = %s", (PROVIDER,))
        values = [
            (
                fact_owner_of_tm[int(row["player_id"])],
                PROVIDER,
                row["date"],
                row["market_value_in_eur"],
                "EUR",
                "CROWD_SOURCED_ESTIMATE",
                VALUATIONS_AS_OF,
                uri_values,
            )
            for row in _rows(directory / "player_valuations.csv.gz")
            if int(row["player_id"]) in tm_ids and row["market_value_in_eur"]
        ]
        cursor.executemany(
            """INSERT INTO fact_player_market_value
               (player_id, provider, valuation_date, amount, currency, valuation_type,
                data_as_of, provenance_raw_object_uri)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            values,
        )
        cursor.execute("DELETE FROM fact_transfer WHERE provider = %s", (PROVIDER,))
        transfers = []
        for row in _rows(directory / "transfers.csv.gz"):
            tm = int(row["player_id"])
            moved = _parse_date(row["transfer_date"])
            # Future-dated rows are contract-end or loan-return markers, not transfers.
            if tm not in tm_ids or moved is None or moved > SNAPSHOT_DATE:
                continue
            fee_text = row["transfer_fee"].strip()
            fee = float(fee_text) if fee_text else None
            transfers.append(
                (
                    fact_owner_of_tm[tm],
                    PROVIDER,
                    f"{tm}-{row['transfer_date']}-{row['from_club_id']}-{row['to_club_id']}",
                    moved,
                    "COMPLETED",
                    fee if fee and fee > 0 else None,
                    "EUR" if fee and fee > 0 else None,
                    bool(fee and fee > 0),
                    "free transfer or loan (fee 0)" if fee == 0 else None
                    if fee is not None
                    else "fee not recorded",
                    VALUATIONS_AS_OF,
                    uri_transfers,
                    row["from_club_name"] or None,
                    row["to_club_name"] or None,
                    row["transfer_season"] or None,
                )
            )
        cursor.executemany(
            """INSERT INTO fact_transfer
               (player_id, provider, provider_transfer_id, transfer_date, transfer_status,
                fee_amount, fee_currency, fee_disclosed, raw_fee_text, data_as_of,
                provenance_raw_object_uri, from_club_name, to_club_name, transfer_season)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            transfers,
        )
        cursor.execute("DELETE FROM player_contract_observation WHERE provider = %s", (PROVIDER,))
        contracts = [
            (
                fact_owner_of_tm[p.tm_player_id],
                PROVIDER,
                p.contract_expires,
                p.current_club,
                date(2026, 6, 12),
                uri_players,
            )
            for p in snapshot_players
            if p.tm_player_id in tm_ids and p.contract_expires
        ]
        cursor.executemany(
            """INSERT INTO player_contract_observation
               (player_id, provider, contract_expires, club_name, observed_as_of,
                provenance_raw_object_uri) VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            contracts,
        )
        report["loaded"] = {
            "valuations": len(values),
            "transfers": len(transfers),
            "contracts": len(contracts),
        }
    connection.commit()
    return report
