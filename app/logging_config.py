"""Structured JSON event log (one object per line) with an allow-list of fields.

Log hygiene is enforced by construction: only fields named in ``ALLOWED_FIELDS`` can
ever be written, so a request body, a name or a stray PAN cannot slip in by accident.
Card ids are opaque tokens; money is a decimal string; timestamps are UTC.
"""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

SERVICE = "fintech-risk-api"
DEFAULT_LOG = Path(__file__).resolve().parent.parent / "logs" / "app.log"
ALLOWED_FIELDS = (
    "card_id",
    "amount",
    "currency",
    "decision",
    "risk_score",
    "velocity_count",
    "merchant_category",
    "request_id",
)


def log_path() -> Path:
    """Log file location; ``RISK_LOG_PATH`` overrides the default (used by tests)."""
    return Path(os.environ.get("RISK_LOG_PATH", DEFAULT_LOG))


def build_record(
    event: str, *, level: str = "INFO", ts: datetime | None = None, **fields: Any
) -> dict[str, Any]:
    """Build a log record. Unknown fields are dropped; naive timestamps are rejected."""
    when = ts if ts is not None else datetime.now(UTC)
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("log timestamp must be timezone-aware")
    record: dict[str, Any] = {
        "ts": when.astimezone(UTC).isoformat(),
        "level": level,
        "service": SERVICE,
        "event": event,
    }
    for name in ALLOWED_FIELDS:
        value = fields.get(name)
        if value is None:
            continue
        record[name] = str(value) if isinstance(value, Decimal) else value
    return record


def write_event(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def emit(event: str, *, level: str = "INFO", ts: datetime | None = None, **fields: Any) -> None:
    write_event(log_path(), build_record(event, level=level, ts=ts, **fields))
