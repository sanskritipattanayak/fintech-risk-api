"""FastAPI routes for the payments-risk service."""

import datetime as dt
import uuid
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.decision import Decision, evaluate
from app.logging_config import emit, log_path
from app.model import FraudModel, generate_transactions, read_csv, train
from app.summary import summarize
from app.velocity import VelocityChecker, to_utc

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"
CARD_ID_PATTERN = r"^card_[0-9a-f]{8}$"


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


@app.get("/decisions/summary")
def decisions_summary(
    date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
) -> dict[str, Any]:
    try:
        day = dt.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=422, detail="date is not a valid calendar day") from None
    return summarize(day, log_path())


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    outcome = evaluate(
        card_id=req.card_id,
        amount=req.amount,
        timestamp=req.timestamp,
        merchant_category=req.merchant_category,
        is_foreign=req.is_foreign,
        card_age_days=req.card_age_days,
        velocity=velocity,
        model=get_model(),
    )
    emit(
        outcome.decision.value,
        level="INFO" if outcome.decision is Decision.APPROVED else "WARNING",
        card_id=req.card_id,
        amount=req.amount,
        currency=req.currency,
        decision=outcome.decision.value,
        risk_score=outcome.risk_score,
        velocity_count=outcome.velocity_count,
        merchant_category=req.merchant_category,
        request_id=uuid.uuid4().hex[:12],
    )
    return ScoreResponse(
        decision=outcome.decision, risk_score=outcome.risk_score, card_id=req.card_id
    )
