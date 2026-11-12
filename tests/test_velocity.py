from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.velocity import VelocityChecker, amount_exceeds_limit, to_utc

T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def test_allows_up_to_max_then_declines() -> None:
    v = VelocityChecker(max_txns=3, window=timedelta(minutes=10))
    results = [v.check_and_record("card_aaaaaaaa", T0 + timedelta(seconds=i)) for i in range(5)]
    assert results == [True, True, True, False, False]


def test_window_expires() -> None:
    v = VelocityChecker(max_txns=1, window=timedelta(minutes=10))
    assert v.check_and_record("card_aaaaaaaa", T0)
    assert not v.check_and_record("card_aaaaaaaa", T0 + timedelta(minutes=9, seconds=59))
    # Window is half-open (ts - window, ts]: an event exactly `window` old is outside it.
    v2 = VelocityChecker(max_txns=1, window=timedelta(minutes=10))
    v2.check_and_record("card_aaaaaaaa", T0)
    assert v2.check_and_record("card_aaaaaaaa", T0 + timedelta(minutes=10))


def test_cards_are_independent() -> None:
    v = VelocityChecker(max_txns=1)
    assert v.check_and_record("card_aaaaaaaa", T0)
    assert v.check_and_record("card_bbbbbbbb", T0)


def test_midnight_utc_boundary_does_not_reset_window() -> None:
    v = VelocityChecker(max_txns=2, window=timedelta(minutes=10))
    before = datetime(2026, 3, 1, 23, 58, tzinfo=UTC)
    after = datetime(2026, 3, 2, 0, 1, tzinfo=UTC)
    assert v.check_and_record("card_aaaaaaaa", before)
    assert v.check_and_record("card_aaaaaaaa", before + timedelta(seconds=30))
    assert not v.check_and_record("card_aaaaaaaa", after)


@pytest.mark.parametrize("hour", [0, 2, 4, 5, 12, 23])
def test_one_transaction_counts_once_at_any_utc_hour(hour: int) -> None:
    # INC-DEMO-001: events at 00:00-05:00 UTC were recorded three times.
    v = VelocityChecker()
    ts = datetime(2026, 3, 1, hour, 30, tzinfo=UTC)
    v.check_and_record("card_aaaaaaaa", ts)
    assert v.count_in_window("card_aaaaaaaa", ts) == 1


@pytest.mark.parametrize("hour", [2, 12])
def test_overnight_burst_uses_same_threshold_as_daytime(hour: int) -> None:
    v = VelocityChecker(max_txns=5, window=timedelta(minutes=10))
    t0 = datetime(2026, 3, 1, hour, 0, tzinfo=UTC)
    results = [
        v.check_and_record("card_aaaaaaaa", t0 + timedelta(seconds=30 * i)) for i in range(6)
    ]
    assert results == [True] * 5 + [False]


def test_non_utc_aware_timestamps_are_normalised() -> None:
    v = VelocityChecker(max_txns=1, window=timedelta(minutes=10))
    plus5 = timezone(timedelta(hours=5))
    assert v.check_and_record("card_aaaaaaaa", datetime(2026, 3, 1, 17, 0, tzinfo=plus5))
    # Same instant expressed in UTC must count against the same window.
    assert not v.check_and_record("card_aaaaaaaa", datetime(2026, 3, 1, 12, 1, tzinfo=UTC))


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValueError):
        to_utc(datetime(2026, 3, 1, 12, 0))  # noqa: DTZ001
    with pytest.raises(ValueError):
        VelocityChecker().check_and_record(
            "card_aaaaaaaa",
            datetime(2026, 3, 1, 12, 0),  # noqa: DTZ001
        )


def test_invalid_config() -> None:
    with pytest.raises(ValueError):
        VelocityChecker(max_txns=0)
    with pytest.raises(ValueError):
        VelocityChecker(window=timedelta(0))


def test_amount_limit_is_strictly_greater_and_decimal() -> None:
    assert not amount_exceeds_limit(Decimal("100.00"), Decimal("100.00"))
    assert amount_exceeds_limit(Decimal("100.01"), Decimal("100.00"))
    # Classic float trap: 0.1 + 0.2 must equal 0.3 with Decimal.
    assert not amount_exceeds_limit(Decimal("0.1") + Decimal("0.2"), Decimal("0.3"))


def test_amount_limit_compares_exactly_beyond_float_precision() -> None:
    assert amount_exceeds_limit(Decimal("100.000000000000001"), Decimal("100"))
    assert amount_exceeds_limit(Decimal("9007199254740993.00"), Decimal("9007199254740992.00"))


def test_amount_limit_rejects_float() -> None:
    with pytest.raises(TypeError):
        amount_exceeds_limit(100.0, Decimal("100"))  # type: ignore[arg-type]
