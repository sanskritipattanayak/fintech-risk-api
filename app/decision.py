"""Scoring decision shared by the API and the traffic simulator.

Keeping this in one place means the simulated production log is produced by exactly
the code that serves requests, not by a lookalike.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.model import FraudModel
from app.velocity import VelocityChecker

RISK_THRESHOLD = 0.8


class Decision(StrEnum):
    APPROVED = "APPROVED"
    DECLINED_VELOCITY = "DECLINED_VELOCITY"
    DECLINED_RISK = "DECLINED_RISK"


@dataclass(frozen=True)
class Outcome:
    decision: Decision
    risk_score: float
    velocity_count: int  # transactions for this card in the window, including this one


def evaluate(
    *,
    card_id: str,
    amount: Decimal,
    timestamp: datetime,
    merchant_category: str,
    is_foreign: bool,
    card_age_days: int,
    velocity: VelocityChecker,
    model: FraudModel,
) -> Outcome:
    """Velocity check first, then the fraud model."""
    allowed = velocity.check_and_record(card_id, timestamp)
    count = velocity.count_in_window(card_id, timestamp)
    if not allowed:
        return Outcome(Decision.DECLINED_VELOCITY, 1.0, count)
    risk = model.score(amount, timestamp, is_foreign, card_age_days, merchant_category)
    decision = Decision.DECLINED_RISK if risk >= RISK_THRESHOLD else Decision.APPROVED
    return Outcome(decision, round(risk, 4), count)
