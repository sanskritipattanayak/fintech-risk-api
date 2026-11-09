#!/usr/bin/env python3
"""SessionStart: put the active policy in front of Claude and the audience."""

from __future__ import annotations

import audit

BANNER = """ACTIVE GUARDRAILS (enforced by hooks, not by trust):
- Restricted data (PAN, SSN, keys) is blocked in prompts, written files and commits.
- .env, secrets/ and presenter notes are unreadable. No network tools.
- No push to main, no force push, no merge. Production deploys need a human approver.
- Tests must be green to commit or finish. Money is Decimal; timestamps are UTC.
- Guardrail files require human approval to change. Decisions are written to the audit log."""


def main() -> None:
    audit.log_event("SessionStart", "info", "banner")
    print(BANNER)


if __name__ == "__main__":
    main()
