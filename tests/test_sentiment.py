from datetime import date

from football_intelligence.sentiment import DatedSentiment, aggregate_sentiment, score_text


def test_sentiment_is_deterministic_and_handles_simple_negation():
    positive = score_text("A brilliant and strong performance")
    assert positive.label == "POSITIVE"
    assert positive.matched_terms == ("brilliant", "strong")
    assert score_text("not great").label == "NEGATIVE"
    assert score_text("ordinary display").label == "NEUTRAL"


def test_sentiment_aggregates_by_date_without_becoming_quality_metric():
    day = date(2026, 1, 1)
    assert aggregate_sentiment([DatedSentiment(day, 1), DatedSentiment(day, -0.5)]) == {day: 0.25}
