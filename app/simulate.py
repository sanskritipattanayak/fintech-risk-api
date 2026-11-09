"""Traffic simulator: runs synthetic transactions through the real decision code.

The resulting log is what the service itself would write, so any defect in
``app/velocity.py`` shows up in the log as a genuine symptom. No hand-edited log lines.
"""

import math
import random
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.decision import Decision, evaluate
from app.logging_config import build_record
from app.model import CATEGORIES, FraudModel, generate_transactions, train
from app.velocity import VelocityChecker

CENT = Decimal("0.01")
DEFAULT_START = datetime(2026, 3, 1, tzinfo=UTC)


@lru_cache(maxsize=1)
def _model() -> FraudModel:
    return train(generate_transactions(2000, seed=0))


def _weight(hour: float) -> float:
    """Relative traffic level by UTC hour: quiet overnight, peak around midday."""
    return 0.35 + 0.65 * max(0.0, math.sin(math.pi * (hour - 4) / 16))


def _draw_events(rng: random.Random, n: int, start: datetime, hours: int) -> list[dict[str, Any]]:
    cards = [(f"card_{rng.getrandbits(32):08x}", rng.randint(5, 3000)) for _ in range(400)]
    span = hours * 3600 - 1
    events: list[dict[str, Any]] = []

    def add(ts: datetime, card: tuple[str, int], base: dict[str, Any]) -> None:
        events.append({"ts": ts, "card": card, **base})

    while len(events) < n:
        offset = rng.uniform(0, span)
        if rng.random() > _weight((offset / 3600) % 24):
            continue
        ts = start + timedelta(seconds=offset)
        card = rng.choice(cards)
        base = {
            "amount": Decimal(str(round(rng.lognormvariate(3.5, 1.1), 2))).quantize(
                CENT, ROUND_HALF_UP
            ),
            "category": rng.choice(CATEGORIES),
            "foreign": rng.random() < 0.08,
        }
        add(ts, card, base)
        if rng.random() < 0.03:  # occasional rapid burst on one card
            for _ in range(rng.randint(1, 5)):
                ts = ts + timedelta(seconds=rng.randint(1, 25))
                if (ts - start).total_seconds() <= span:
                    add(ts, card, base)
    events.sort(key=lambda e: e["ts"])
    return events[:n]


def simulate(
    n: int = 4000, seed: int = 42, start: datetime = DEFAULT_START, hours: int = 24
) -> list[dict[str, Any]]:
    """Return ``n`` log records covering ``hours`` hours from ``start`` (UTC), in time order."""
    rng = random.Random(seed)
    velocity = VelocityChecker()
    model = _model()
    records: list[dict[str, Any]] = []
    for e in _draw_events(rng, n, start, hours):
        card_id, age = e["card"]
        out = evaluate(
            card_id=card_id,
            amount=e["amount"],
            timestamp=e["ts"],
            merchant_category=e["category"],
            is_foreign=e["foreign"],
            card_age_days=age,
            velocity=velocity,
            model=model,
        )
        records.append(
            build_record(
                out.decision.value,
                level="INFO" if out.decision is Decision.APPROVED else "WARNING",
                ts=e["ts"],
                card_id=card_id,
                amount=e["amount"],
                currency="USD",
                decision=out.decision.value,
                risk_score=out.risk_score,
                velocity_count=out.velocity_count,
                merchant_category=e["category"],
                request_id=f"{rng.getrandbits(48):012x}",
            )
        )
    return records


def write_log(records: list[dict[str, Any]], path: Path) -> None:
    """Overwrite ``path`` with the records as JSON lines."""
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records), encoding="utf-8"
    )
