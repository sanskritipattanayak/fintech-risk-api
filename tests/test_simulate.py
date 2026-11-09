from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from app.simulate import simulate

START = datetime(2026, 3, 1, tzinfo=UTC)
EVENTS = {"APPROVED", "DECLINED_VELOCITY", "DECLINED_RISK"}


def test_simulation_is_deterministic() -> None:
    assert simulate(n=300, seed=1) == simulate(n=300, seed=1)


def test_records_cover_24h_utc_in_time_order_with_valid_schema() -> None:
    records = simulate(n=600, seed=2, start=START)
    stamps = [datetime.fromisoformat(r["ts"]) for r in records]
    assert stamps == sorted(stamps)
    assert stamps[0] >= START and stamps[-1] < START + timedelta(hours=24)
    for r in records:
        assert r["event"] in EVENTS and r["decision"] == r["event"]
        assert r["card_id"].startswith("card_") and r["ts"].endswith("+00:00")
        assert r["level"] == ("INFO" if r["event"] == "APPROVED" else "WARNING")


@pytest.mark.xfail(
    strict=True,
    reason="seeded demo defect in app/velocity.py (INC midnight spike); remove when fixed",
)
def test_correct_code_has_no_midnight_spike() -> None:
    records = simulate(n=1500, seed=3, start=START)
    declines = Counter(
        datetime.fromisoformat(r["ts"]).hour for r in records if r["event"] == "DECLINED_VELOCITY"
    )
    totals = Counter(datetime.fromisoformat(r["ts"]).hour for r in records)
    shares = [declines[h] / totals[h] for h in totals]
    assert max(shares) < 0.10, "velocity declines should stay low around the clock"
    assert declines[0] <= 3 * max(1, sorted(declines.values())[len(declines) // 2])
