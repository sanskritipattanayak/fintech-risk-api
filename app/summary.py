"""Declined-decision counts by reason for one UTC day, read from the event log.

Read-only: the log is opened for reading, never written. The result is built from a
fixed whitelist (date, total, reason counts); no log field is passed through.
"""

import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any


def _event_time(raw: Any) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if ts.tzinfo is None or ts.utcoffset() is None:
        return None
    return ts.astimezone(UTC)


def summarize(day: date, path: Path) -> dict[str, Any]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    by_reason: dict[str, int] = {}
    seen: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                decision, ts = event.get("decision"), _event_time(event.get("ts"))
                if not isinstance(decision, str) or not decision.startswith("DECLINED"):
                    continue
                if ts is None or not start <= ts < end:
                    continue
                rid = event.get("request_id")
                if rid is not None:
                    if rid in seen:
                        continue
                    seen.add(rid)
                by_reason[decision] = by_reason.get(decision, 0) + 1
    return {
        "date": day.isoformat(),
        "total_declined": sum(by_reason.values()),
        "by_reason": by_reason,
    }
