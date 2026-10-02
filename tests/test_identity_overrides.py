import json

import pytest
from pydantic import ValidationError

from football_intelligence.identity_overrides import load_identity_overrides


def test_override_file_requires_unique_ids_and_review_evidence(tmp_path):
    path = tmp_path / "overrides.json"
    record = {
        "override_id": "review-1",
        "version": 1,
        "action": "LINK_PROVIDER_PLAYER",
        "provider": "wyscout_open",
        "provider_player_id": "8726",
        "canonical_player_id": 1,
        "reason": "Verified using official date of birth.",
        "approved_by": "reviewer",
        "approved_at": "2026-09-28T12:00:00Z",
    }
    path.write_text(json.dumps([record]), encoding="utf-8")
    assert load_identity_overrides(path)[0].provider_player_id == "8726"
    path.write_text(json.dumps([record, record]), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_identity_overrides(path)


def test_override_rejects_naive_approval_time(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text(
        json.dumps(
            [
                {
                    "override_id": "review-1",
                    "version": 1,
                    "action": "LINK_PROVIDER_PLAYER",
                    "provider": "wyscout_open",
                    "provider_player_id": "8726",
                    "canonical_player_id": 1,
                    "reason": "Verified using official date of birth.",
                    "approved_by": "reviewer",
                    "approved_at": "2026-09-28T12:00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="timezone"):
        load_identity_overrides(path)
