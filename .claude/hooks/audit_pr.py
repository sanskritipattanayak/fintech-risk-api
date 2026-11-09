#!/usr/bin/env python3
"""PostToolUse (Bash): record PR creation in the audit trail."""

from __future__ import annotations

import audit
from common import read_input


def main() -> None:
    data = read_input()
    cmd = data.get("tool_input", {}).get("command", "")
    if "gh pr create" in cmd:
        audit.log_event("PostToolUse", "info", "pr-created", "Bash", cmd)


if __name__ == "__main__":
    main()
