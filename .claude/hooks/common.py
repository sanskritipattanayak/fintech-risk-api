"""Shared plumbing for hook scripts. Stdlib only, Python 3.9 compatible."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit  # noqa: E402


def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def deny(event: str, rule: str, reason: str, tool: str = "", subject: str = "") -> None:
    """Block the action. Exit code 2 sends stderr back to Claude as feedback."""
    audit.log_event(event, "deny", rule, tool, subject)
    print(f"BLOCKED by policy [{rule}]: {reason}", file=sys.stderr)
    sys.exit(2)


def ask(event: str, rule: str, reason: str, tool: str = "", subject: str = "") -> None:
    """Escalate to the human: the user is prompted to approve or reject."""
    audit.log_event(event, "ask", rule, tool, subject)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"[{rule}] {reason}",
                }
            }
        )
    )
    sys.exit(0)
