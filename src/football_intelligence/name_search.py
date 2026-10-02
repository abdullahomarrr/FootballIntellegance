"""Typo-tolerant player-name search for the current-season stats feeds."""

from __future__ import annotations

from difflib import SequenceMatcher

from football_intelligence.market_snapshot import fold

MIN_TOKEN_RATIO = 0.8
MIN_WHOLE_RATIO = 0.85


def _token_score(query_token: str, name_tokens: list[str]) -> float:
    best = 0.0
    for token in name_tokens:
        if query_token in token:
            return 1.0
        if len(query_token) >= 4:
            best = max(best, SequenceMatcher(None, query_token, token).ratio())
    return best if best >= MIN_TOKEN_RATIO else 0.0


def name_score(query: str, name: str) -> float:
    """0 when the name does not match; otherwise a score where 1.0 is an exact token match.

    Every query token must appear in the name or be a close spelling of one of its words, so
    "raphina" finds "Raphinha" but "lamine" does not find every Lamine-adjacent name.
    """
    query_tokens = fold(query).split()
    name_tokens = fold(name).split()
    if not query_tokens or not name_tokens:
        return 0.0
    scores = [_token_score(token, name_tokens) for token in query_tokens]
    if all(scores):
        return sum(scores) / len(scores)
    whole = SequenceMatcher(None, "".join(query_tokens), "".join(name_tokens)).ratio()
    return whole if whole >= MIN_WHOLE_RATIO else 0.0
