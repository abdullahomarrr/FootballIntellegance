"""Short, human display names for players whose canonical names are long legal names."""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

from football_intelligence.env import load_env_file

LlmCaller = Callable[[str, str], str]

BATCH_SIZE = 60
MAX_ATTEMPTS = 3
_SHORT_RE = re.compile(r"^([A-Za-zÀ-ɏ])\.\s*(.+)$")

SYSTEM_PROMPT = (
    "You shorten football players' legal names to the name they are commonly known by "
    "in media (e.g. 'Lionel Andres Messi Cuccittini' -> 'Lionel Messi'). "
    "Use ONLY words that already appear in the given name; never invent or add words. "
    'Reply with a JSON array of objects {"id": <int>, "display_name": <string>} '
    "and nothing else."
)


def clean(text: str) -> str:
    """Strip soft hyphens and collapse whitespace."""
    return " ".join(text.replace("­", "").split())


def fold(text: str) -> str:
    """Lowercase, diacritic-free, alphanumeric-only form of a token or name."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", stripped.replace("ø", "o").replace("ł", "l"))


def tokens(name: str) -> list[str]:
    return [t for t in clean(name).split(" ") if t]


def expand_initial(canonical: str, short_name: str) -> str | None:
    """Turn a Wyscout short name such as 'L. Messi' into 'Lionel Messi'."""
    match = _SHORT_RE.match(clean(short_name))
    canon = tokens(canonical)
    if not match or not canon:
        return None
    rest = match.group(2).strip()
    if not rest or not fold(canon[0]).startswith(fold(match.group(1))):
        return None
    return f"{canon[0]} {rest}"


def is_grounded(candidate: str, canonical: str, mononyms: Iterable[str] = ()) -> bool:
    """Accept an LLM name only if it is built from canonical tokens (or a known alias)."""
    candidate = clean(candidate)
    cand_tokens = tokens(candidate)
    if not cand_tokens or len(candidate) > len(clean(canonical)):
        return False
    if fold(candidate) in {fold(m) for m in mononyms if fold(m)}:
        return True
    canon_set = {fold(t) for t in tokens(canonical)}
    return all(fold(t) and fold(t) in canon_set for t in cand_tokens)


def choose_rule_based(
    canonical: str, statsbomb: Sequence[str], wyscout: Sequence[str]
) -> tuple[str, str] | None:
    """Rules 1-3. Returns (display_name, source) or None when the LLM is needed."""
    canonical = clean(canonical)
    for alias in statsbomb:
        if clean(alias):
            return clean(alias), "statsbomb_nickname"
    if len(tokens(canonical)) <= 2:
        return canonical, "canonical"
    for short in wyscout:
        expanded = expand_initial(canonical, short)
        if expanded:
            return expanded, "wyscout_short"
    return None


def parse_llm_response(raw: str) -> dict[int, str]:
    """Extract {id: display_name} from a JSON array, tolerating code fences and prose."""
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("no JSON array in LLM response")
    payload = json.loads(raw[start : end + 1])
    result: dict[int, str] = {}
    for item in payload:
        if isinstance(item, dict) and "id" in item and isinstance(item.get("display_name"), str):
            result[int(item["id"])] = item["display_name"]
    return result


def llm_batch(
    caller: LlmCaller,
    batch: Sequence[Mapping[str, Any]],
    sleep: Callable[[float], None] = time.sleep,
) -> dict[int, str]:
    """Ask the LLM about one batch; retry twice on failure. Returns raw suggestions."""
    lines = [
        {
            "id": int(r["player_id"]),
            "name": r["canonical_name"],
            "nationality": r.get("nationality"),
        }
        for r in batch
    ]
    prompt = "Names:\n" + json.dumps(lines, ensure_ascii=False)
    for attempt in range(MAX_ATTEMPTS):
        try:
            return parse_llm_response(caller(SYSTEM_PROMPT, prompt))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            if attempt < MAX_ATTEMPTS - 1:
                limited = (
                    isinstance(error, httpx.HTTPStatusError)
                    and error.response.status_code == 429
                )
                sleep((20.0 if limited else 2.0) * (attempt + 1))
    return {}


def openai_compatible_caller(client: httpx.Client) -> LlmCaller | None:
    load_env_file()
    base_url = os.environ.get("RESEARCH_LLM_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    model = os.environ.get("RESEARCH_LLM_MODEL", "llama3.2")
    api_key = os.environ.get("RESEARCH_LLM_API_KEY", "")
    effort = os.environ.get("RESEARCH_LLM_REASONING_EFFORT", "").strip()

    def call(system: str, user: str) -> str:
        headers = {"content-type": "application/json"}
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
        response = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "temperature": 0,
                **({"reasoning_effort": effort} if effort else {}),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=180,
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        return str(choices[0]["message"]["content"]) if choices else ""

    return call


@dataclass
class DisplayNameResult:
    total: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    llm_rejected: int = 0
    llm_missing: int = 0


def populate_display_names(
    connection: Any,
    *,
    use_llm: bool = True,
    caller: LlmCaller | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> DisplayNameResult:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT player_id, canonical_name, nationality_codes, "
            "CASE WHEN display_name_source = 'llm' THEN display_name END "
            "FROM dim_player ORDER BY player_id"
        )
        players = cursor.fetchall()
        cursor.execute(
            "SELECT player_id, source, alias FROM player_alias "
            "WHERE source IN ('statsbomb_open','wyscout_open') ORDER BY player_alias_id"
        )
        aliases: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for player_id, source, alias in cursor.fetchall():
            aliases[player_id][source].append(alias)

    chosen: dict[int, tuple[str, str]] = {}
    pending: list[dict[str, Any]] = []
    for player_id, canonical, nationalities, previous_llm in players:
        found = choose_rule_based(
            canonical,
            aliases[player_id]["statsbomb_open"],
            aliases[player_id]["wyscout_open"],
        )
        if found:
            chosen[player_id] = found
        elif previous_llm and is_grounded(previous_llm, canonical):
            chosen[player_id] = (previous_llm, "llm")  # keep earlier LLM result across reruns
        else:
            pending.append(
                {
                    "player_id": player_id,
                    "canonical_name": clean(canonical),
                    "nationality": ", ".join(nationalities or []) or None,
                }
            )

    result = DisplayNameResult(total=len(players))
    active_caller: LlmCaller | None = caller
    client: httpx.Client | None = None
    if use_llm and active_caller is None:
        client = httpx.Client()
        active_caller = openai_compatible_caller(client)
    try:
        for offset in range(0, len(pending), BATCH_SIZE):
            batch = pending[offset : offset + BATCH_SIZE]
            suggestions = (
                llm_batch(active_caller, batch, sleep) if use_llm and active_caller else {}
            )
            for row in batch:
                pid, canonical = row["player_id"], row["canonical_name"]
                suggestion = suggestions.get(pid)
                if suggestion is None:
                    result.llm_missing += 1
                elif is_grounded(suggestion, canonical, aliases[pid]["statsbomb_open"]):
                    chosen[pid] = (clean(suggestion), "llm")
                    continue
                else:
                    result.llm_rejected += 1
                chosen[pid] = (canonical, "canonical")
            sleep(4.0)
    finally:
        if client is not None:
            client.close()

    canonical_by_id = {p[0]: clean(p[1]) for p in players}
    with connection.cursor() as cursor:
        for pid, (name, source) in chosen.items():
            cursor.execute(
                "UPDATE dim_player SET display_name = %s, display_name_source = %s "
                "WHERE player_id = %s",
                (name or canonical_by_id[pid], source, pid),
            )
    connection.commit()
    for _, source in chosen.values():
        result.by_source[source] = result.by_source.get(source, 0) + 1
    return result
