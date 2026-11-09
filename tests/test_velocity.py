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


def test_amount_limit_rejects_float() -> None:
    with pytest.raises(TypeError):
        amount_exceeds_limit(100.0, Decimal("100"))  # type: ignore[arg-type]
