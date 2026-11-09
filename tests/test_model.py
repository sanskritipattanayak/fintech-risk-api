from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.model import CSV_COLUMNS, build_features, generate_transactions, train


@pytest.fixture(scope="module")
def df():
    return generate_transactions(n=1500, seed=7)


def test_generation_is_deterministic() -> None:
    a = generate_transactions(200, seed=1)
    b = generate_transactions(200, seed=1)
    assert a.equals(b)


def test_schema_and_amount_strings(df) -> None:
    assert list(df.columns) == CSV_COLUMNS
    assert all(isinstance(a, str) for a in df["amount"])
    assert all(Decimal(a) > 0 for a in df["amount"])
    assert df["card_id"].str.fullmatch(r"card_[0-9a-f]{8}").all()


def test_both_classes_present(df) -> None:
    assert 0.02 < df["is_fraud"].mean() < 0.6


def test_scores_in_range_and_risky_beats_safe(df) -> None:
    model = train(df)
    ts = datetime(2026, 3, 1, 3, 0, tzinfo=UTC)
    risky = model.score(Decimal("900.00"), ts, True, 5, "electronics")
    safe = model.score(Decimal("12.00"), ts.replace(hour=14), False, 2000, "grocery")
    assert 0.0 <= safe <= 1.0 and 0.0 <= risky <= 1.0
    assert risky > safe


def test_features_reject_naive_timestamp() -> None:
    with pytest.raises(ValueError):
        build_features(Decimal("10"), datetime(2026, 3, 1), False, 10, "fuel")  # noqa: DTZ001
