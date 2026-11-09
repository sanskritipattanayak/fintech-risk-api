"""FastAPI routes for the payments-risk service."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from app.model import FraudModel, generate_transactions, read_csv, train
from app.velocity import VelocityChecker, to_utc

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"
RISK_THRESHOLD = 0.8
CARD_ID_PATTERN = r"^card_[0-9a-f]{8}$"


class Decision(StrEnum):
    APPROVED = "APPROVED"
    DECLINED_VELOCITY = "DECLINED_VELOCITY"
    DECLINED_RISK = "DECLINED_RISK"


class ScoreRequest(BaseModel):
    card_id: Annotated[str, Field(pattern=CARD_ID_PATTERN)]
    amount: Annotated[Decimal, Field(gt=Decimal("0"), max_digits=12, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] = "USD"
    timestamp: datetime
    merchant_category: str = "online"
    is_foreign: bool = False
    card_age_days: Annotated[int, Field(ge=0)] = 365

    @field_validator("timestamp")
    @classmethod
    def _aware_utc(cls, v: datetime) -> datetime:
        return to_utc(v)  # naive values raise, which pydantic reports as a 422


class ScoreResponse(BaseModel):
    decision: Decision
    risk_score: float
    card_id: str


@lru_cache(maxsize=1)
def get_model() -> FraudModel:
    df = read_csv(DATA_PATH) if DATA_PATH.exists() else generate_transactions()
    return train(df)


velocity = VelocityChecker()
app = FastAPI(title="fintech-risk-api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    if not velocity.check_and_record(req.card_id, req.timestamp):
        return ScoreResponse(
            decision=Decision.DECLINED_VELOCITY, risk_score=1.0, card_id=req.card_id
        )
    risk = get_model().score(
        req.amount, req.timestamp, req.is_foreign, req.card_age_days, req.merchant_category
    )
    decision = Decision.DECLINED_RISK if risk >= RISK_THRESHOLD else Decision.APPROVED
    return ScoreResponse(decision=decision, risk_score=round(risk, 4), card_id=req.card_id)
