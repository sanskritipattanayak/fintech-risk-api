import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.logging_config import ALLOWED_FIELDS, build_record, write_event

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "hooks"))
import dlp  # noqa: E402

BODY = {
    "card_id": "card_0a1b2c3d",
    "amount": "25.50",
    "timestamp": "2026-03-01T12:00:00Z",
    "merchant_category": "grocery",
    "card_age_days": 900,
}


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_record_is_allowlisted_and_utc() -> None:
    rec = build_record("APPROVED", card_id="card_0a1b2c3d", amount=Decimal("25.50"), body="x")
    assert set(rec) <= {"ts", "level", "service", "event", *ALLOWED_FIELDS}
    assert "body" not in rec  # unknown fields are dropped, never logged
    assert rec["amount"] == "25.50"  # Decimal serialised as a string, never a float
    assert rec["ts"].endswith("+00:00")


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValueError):
        build_record("APPROVED", ts=datetime(2026, 3, 1, 12, 0))  # noqa: DTZ001


def test_write_event_appends_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "x" / "app.log"
    write_event(path, build_record("APPROVED", card_id="card_0a1b2c3d"))
    write_event(path, build_record("DECLINED_VELOCITY", level="WARNING"))
    assert [e["event"] for e in read_events(path)] == ["APPROVED", "DECLINED_VELOCITY"]


def test_api_logs_one_event_per_decision(client: TestClient, log_path: Path) -> None:
    client.post("/score", json=BODY)
    (event,) = read_events(log_path)
    assert event["event"] == "APPROVED" and event["level"] == "INFO"
    assert event["card_id"] == "card_0a1b2c3d"
    assert event["amount"] == "25.50"
    assert {"risk_score", "velocity_count", "request_id", "decision"} <= set(event)


def test_velocity_decline_is_logged_as_warning(client: TestClient, log_path: Path) -> None:
    for _ in range(7):
        client.post("/score", json=BODY)
    events = read_events(log_path)
    declined = [e for e in events if e["event"] == "DECLINED_VELOCITY"]
    assert len(declined) == 2
    assert all(e["level"] == "WARNING" and e["velocity_count"] >= 6 for e in declined)


def test_log_never_contains_request_body_or_restricted_data(
    client: TestClient, log_path: Path
) -> None:
    client.post("/score", json={**BODY, "card_id": "4111" + "1111" + "1111" + "1111"})  # 422
    client.post("/score", json=BODY)
    text = log_path.read_text()
    assert dlp.scan_text(text) == []
    for key in ("merchant_category_secret", "card_age_days", "is_foreign"):
        assert key not in text
