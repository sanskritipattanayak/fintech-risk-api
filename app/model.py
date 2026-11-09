"""Fraud model (scikit-learn) trained on synthetic data only.

Money stays ``Decimal`` everywhere in the service. The model feature matrix is
the one deliberate boundary where amounts become floats (log-scaled), because
scikit-learn needs numeric arrays. Nothing is converted back into money.
"""

import csv
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

CATEGORIES = ["grocery", "fuel", "travel", "electronics", "dining", "online", "atm"]
CATEGORY_RISK = {"electronics": 0.25, "online": 0.2, "atm": 0.2, "travel": 0.1}
FEATURES = ["log_amount", "hour_utc", "is_foreign", "card_age_days", "category_code"]
CSV_COLUMNS = [
    "txn_id",
    "card_id",
    "timestamp",
    "amount",
    "currency",
    "merchant_category",
    "is_foreign",
    "card_age_days",
    "is_fraud",
]
CENT = Decimal("0.01")


def _card_id(rng: random.Random) -> str:
    return f"card_{rng.getrandbits(32):08x}"


def generate_transactions(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate ``n`` synthetic transactions. Amounts are decimal strings.

    Card ids are opaque random tokens; there is no PAN, name or contact data.
    """
    rng = random.Random(seed)
    cards = [(_card_id(rng), rng.randint(5, 3000)) for _ in range(400)]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(n):
        card_id, age = rng.choice(cards)
        ts = start + timedelta(seconds=rng.randint(0, 30 * 24 * 3600))
        category = rng.choice(CATEGORIES)
        is_foreign = rng.random() < 0.08
        amount = Decimal(str(round(rng.lognormvariate(3.5, 1.1), 2))).quantize(CENT, ROUND_HALF_UP)
        p = 0.01 + CATEGORY_RISK.get(category, 0.0) * 0.2
        if is_foreign:
            p += 0.15
        if amount > Decimal("400"):
            p += 0.2
        if ts.hour < 5:
            p += 0.1
        if age < 30:
            p += 0.1
        rows.append(
            {
                "txn_id": f"txn_{i:06d}",
                "card_id": card_id,
                "timestamp": ts.isoformat(),
                "amount": str(amount),
                "currency": "USD",
                "merchant_category": category,
                "is_foreign": is_foreign,
                "card_age_days": age,
                "is_fraud": rng.random() < min(p, 0.9),
            }
        )
    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write the dataset with amounts preserved as decimal strings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, quoting=csv.QUOTE_NONNUMERIC)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"amount": str})


def build_features(
    amount: Decimal,
    timestamp: datetime,
    is_foreign: bool,
    card_age_days: int,
    category: str,
) -> list[float]:
    """Feature vector for one transaction (the Decimal -> float boundary)."""
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    hour = timestamp.astimezone(UTC).hour
    code = CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES)
    return [float(np.log1p(float(amount))), hour, int(is_foreign), card_age_days, code]


def _frame_to_matrix(df: pd.DataFrame) -> np.ndarray:
    rows = []
    for r in df.itertuples():
        rows.append(
            build_features(
                Decimal(r.amount),
                datetime.fromisoformat(r.timestamp),
                bool(r.is_foreign),
                int(r.card_age_days),
                r.merchant_category,
            )
        )
    return np.array(rows)


@dataclass
class FraudModel:
    """Thin wrapper so the API depends on ``score`` and not on scikit-learn."""

    clf: GradientBoostingClassifier

    def score(
        self,
        amount: Decimal,
        timestamp: datetime,
        is_foreign: bool,
        card_age_days: int,
        category: str,
    ) -> float:
        """Fraud probability in [0, 1]."""
        x = np.array([build_features(amount, timestamp, is_foreign, card_age_days, category)])
        return float(self.clf.predict_proba(x)[0, 1])


def train(df: pd.DataFrame, seed: int = 0) -> FraudModel:
    """Train on a transactions frame (must contain the ``is_fraud`` label)."""
    x = _frame_to_matrix(df)
    y = df["is_fraud"].astype(bool).to_numpy()
    clf = GradientBoostingClassifier(random_state=seed, n_estimators=60, max_depth=3)
    clf.fit(x, y)
    return FraudModel(clf)
