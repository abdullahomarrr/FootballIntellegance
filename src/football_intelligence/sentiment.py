from __future__ import annotations

from dataclasses import dataclass
from datetime import date

POSITIVE = frozenset({"excellent", "great", "impressive", "strong", "brilliant", "improved", "fit"})
NEGATIVE = frozenset({"poor", "weak", "awful", "injured", "struggling", "declined", "error"})
NEGATORS = frozenset({"not", "never", "no"})


@dataclass(frozen=True)
class SentimentResult:
    score: float
    label: str
    matched_terms: tuple[str, ...]
    model_version: str = "football_lexicon_v1"


@dataclass(frozen=True)
class DatedSentiment:
    observed_on: date
    score: float


def score_text(text: str) -> SentimentResult:
    tokens = [token.strip(".,!?;:'\"()[]").casefold() for token in text.split()]
    contributions: list[tuple[str, int]] = []
    for index, token in enumerate(tokens):
        polarity = 1 if token in POSITIVE else -1 if token in NEGATIVE else 0
        if polarity:
            if index and tokens[index - 1] in NEGATORS:
                polarity *= -1
            contributions.append((token, polarity))
    score = sum(value for _, value in contributions) / len(contributions) if contributions else 0.0
    rounded = round(score, 4)
    label = "POSITIVE" if rounded > 0.15 else "NEGATIVE" if rounded < -0.15 else "NEUTRAL"
    return SentimentResult(rounded, label, tuple(term for term, _ in contributions))


def aggregate_sentiment(items: list[DatedSentiment]) -> dict[date, float]:
    grouped: dict[date, list[float]] = {}
    for item in items:
        grouped.setdefault(item.observed_on, []).append(item.score)
    return {day: round(sum(values) / len(values), 4) for day, values in sorted(grouped.items())}
