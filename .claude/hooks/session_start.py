#!/usr/bin/env python3
"""SessionStart: put the active policy in front of Claude and the audience."""

from __future__ import annotations

import subprocess

import audit

BANNER = """ACTIVE GUARDRAILS (enforced by hooks, not by trust):
- Restricted data (PAN, SSN, keys) is blocked in prompts, written files and commits.
- .env, secrets/ and presenter notes are unreadable. No network tools.
- No push to main, no force push, no merge. Production deploys need a human approver.
- Tests must be green to commit or finish. Money is Decimal; timestamps are UTC.
- Guardrail files require human approval to change. Decisions are written to the audit log."""


def ensure_git_hooks() -> str:
    """Point git at the versioned hooks so commit/push are gated however they are run."""
    root = audit.project_dir()
    if not (root / ".githooks").is_dir():
        return ""
    current = subprocess.run(
        ["git", "config", "--local", "core.hooksPath"], capture_output=True, text=True, cwd=root
    ).stdout.strip()
    if current != ".githooks":
        subprocess.run(["git", "config", "--local", "core.hooksPath", ".githooks"], cwd=root)
        audit.log_event("SessionStart", "info", "git-hooks-enabled")
        return "\n- Git pre-commit and pre-push hooks were just enabled for this clone."
    return "\n- Git pre-commit and pre-push hooks are active."


def main() -> None:
    audit.log_event("SessionStart", "info", "banner")
    print(BANNER + ensure_git_hooks())


if __name__ == "__main__":
    main()
