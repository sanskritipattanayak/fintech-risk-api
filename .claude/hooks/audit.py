"""Append-only audit trail for guardrail decisions. Stdlib only.

Records what was decided and why, never the raw prompt, command or data: the
subject is stored as a SHA-256 digest so a reviewer can match it to evidence
without the audit log itself becoming a data-leak surface.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def log_event(event: str, decision: str, rule: str, tool: str = "", subject: str = "") -> None:
    path = project_dir() / ".claude" / "audit" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "decision": decision,
        "rule": rule,
        "tool": tool,
        "subject_sha256": hashlib.sha256(subject.encode()).hexdigest()[:16] if subject else "",
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
