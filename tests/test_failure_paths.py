import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from football_intelligence.api import app
from football_intelligence.backfill import run_backfill
from football_intelligence.providers.api_football import BASE_URL, APIFootballAdapter
from football_intelligence.providers.statsbomb_open import EVENTS_URL, StatsBombOpenAdapter


def test_timeout_is_checkpointed_without_claiming_success_and_retry_recovers(tmp_path):
    checkpoint = tmp_path / "timeout.json"
    attempts = 0

    def transient_timeout(_: int) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("provider timed out")

    first = run_backfill([42], checkpoint_path=checkpoint, ingest_match=transient_timeout)
    persisted = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert first.succeeded == 0
    assert first.failed == 1
    assert persisted["completed"] == []
    assert "ReadTimeout" in persisted["failures"]["42"]

    retry = run_backfill([42], checkpoint_path=checkpoint, ingest_match=transient_timeout)
    assert retry.succeeded == 1
    assert retry.failures == {}


@respx.mock
def test_rate_limit_is_explicit_http_failure_not_empty_coverage():
    respx.get(f"{BASE_URL}/leagues", params={"id": 39}).mock(
        return_value=httpx.Response(429, json={"errors": {"rateLimit": "limit reached"}})
    )

    with pytest.raises(httpx.HTTPStatusError) as error:
        APIFootballAdapter("redacted-test-key").discover_league(39)

    assert error.value.response.status_code == 429


@respx.mock
def test_malformed_provider_payload_is_rejected_not_coerced_to_empty():
    match_id = 123
    respx.get(EVENTS_URL.format(match_id=match_id)).mock(
        return_value=httpx.Response(200, json={"events": []})
    )

    with pytest.raises(ValueError, match="events payload must be a list"):
        StatsBombOpenAdapter().fetch_events(match_id)


def test_missing_required_request_field_returns_structured_422():
    response = TestClient(app).post(
        "/squad/optimize",
        json={"needs": ["ST"], "candidates": []},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(item["loc"][-1] == "budget" and item["type"] == "missing" for item in detail)


def test_database_failure_returns_500_without_fabricated_data(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.players",
        lambda *_: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    response = TestClient(app, raise_server_exceptions=False).get("/players")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "data" not in response.json()


def test_unknown_player_identity_returns_not_found(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.player_detail", lambda _: None)
    response = TestClient(app).get("/players/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"
