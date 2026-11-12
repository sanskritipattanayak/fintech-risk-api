"""Decline summary endpoint tests (spec: docs/specs/decline-summary.spec.md)."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.logging_config import build_record, write_event

V, R, A = "DECLINED_VELOCITY", "DECLINED_RISK", "APPROVED"
CARD, AMOUNT = "card_0a1b2c3d", "4242.17"


def _log(path: Path, *events: tuple[str, str, str]) -> None:
    for ts, decision, rid in events:
        write_event(
            path,
            build_record(
                decision,
                ts=datetime.fromisoformat(ts),
                decision=decision,
                request_id=rid,
                card_id=CARD,
                amount=Decimal(AMOUNT),
            ),
        )


def _get(client: TestClient, day: str):
    return client.get("/decisions/summary", params={"date": day})


def test_ac1_counts_declines_by_reason(client: TestClient, log_path: Path) -> None:
    d = "2026-03-01T10:00:00+00:00"
    _log(log_path, (d, V, "r1"), (d, V, "r2"), (d, R, "r3"), (d, A, "r4"), (d, A, "r5"))
    body = _get(client, "2026-03-01").json()
    assert body["total_declined"] == 3
    assert body["by_reason"] == {V: 2, R: 1}


@pytest.fixture()
def boundary(log_path: Path) -> None:
    _log(
        log_path,
        ("2026-03-01T23:59:59.999+00:00", V, "r1"),
        ("2026-03-02T00:00:00.000+00:00", R, "r2"),
    )


def test_ac2_boundary_last_millisecond_belongs_to_day_one(client, boundary) -> None:
    assert _get(client, "2026-03-01").json()["by_reason"] == {V: 1}


def test_ac2_boundary_midnight_belongs_to_next_day(client, boundary) -> None:
    assert _get(client, "2026-03-02").json()["by_reason"] == {R: 1}


def test_ac3_duplicate_request_id_counted_once(client: TestClient, log_path: Path) -> None:
    d = "2026-03-01T10:00:00+00:00"
    _log(log_path, (d, V, "dup"), (d, V, "dup"))
    assert _get(client, "2026-03-01").json()["total_declined"] == 1


def test_ac4_malformed_date_returns_422_naming_date(client: TestClient) -> None:
    r = _get(client, "2026-13-40")
    assert r.status_code == 422 and "date" in r.text


def test_ac4_missing_date_returns_422_naming_date(client: TestClient) -> None:
    r = client.get("/decisions/summary")
    assert r.status_code == 422 and "date" in r.text


def test_ac5_response_has_no_log_fields(client: TestClient, log_path: Path) -> None:
    _log(log_path, ("2026-03-01T10:00:00+00:00", V, "rid-secret-1"))
    r = _get(client, "2026-03-01")
    assert set(r.json()) == {"date", "total_declined", "by_reason"}
    assert not any(s in r.text for s in (CARD, AMOUNT, "rid-secret-1"))


def test_ac6_endpoint_does_not_write_log(client: TestClient, log_path: Path) -> None:
    _log(log_path, ("2026-03-01T10:00:00+00:00", V, "r1"))
    before, mtime = log_path.read_bytes(), log_path.stat().st_mtime_ns
    assert _get(client, "2026-03-01").status_code == 200
    assert log_path.read_bytes() == before and log_path.stat().st_mtime_ns == mtime


def test_ac7_no_declines_returns_zero(client: TestClient, log_path: Path) -> None:
    _log(log_path, ("2026-03-01T10:00:00+00:00", A, "r1"))
    r = _get(client, "2026-03-01")
    assert r.status_code == 200
    assert (r.json()["total_declined"], r.json()["by_reason"]) == (0, {})


def test_ac7_missing_log_file_returns_zero(client: TestClient, log_path: Path) -> None:
    r = _get(client, "2026-03-01")
    assert r.status_code == 200
    assert (r.json()["total_declined"], r.json()["by_reason"]) == (0, {})
    assert not log_path.exists()


def test_x1_offset_timestamps_converted_to_utc(client: TestClient, log_path: Path) -> None:
    _log(log_path, ("2026-03-01T23:30:00-05:00", V, "r1"))  # 2026-03-02T04:30Z
    assert _get(client, "2026-03-01").json()["total_declined"] == 0
    assert _get(client, "2026-03-02").json()["total_declined"] == 1


def test_x2_malformed_log_lines_are_skipped(client: TestClient, log_path: Path) -> None:
    _log(log_path, ("2026-03-01T10:00:00+00:00", V, "r1"))
    with log_path.open("a") as fh:
        fh.write('\nnot json\n[1]\n{"ts":"2026-03-01T10:00:00","decision":"DECLINED_RISK"}\n')
    assert _get(client, "2026-03-01").json()["by_reason"] == {V: 1}


@pytest.mark.parametrize("bad", ["2026-3-1", "20260301", "2026-03-01T00:00:00Z"])
def test_x4_non_iso_date_formats_rejected(client: TestClient, bad: str) -> None:
    assert _get(client, bad).status_code == 422
