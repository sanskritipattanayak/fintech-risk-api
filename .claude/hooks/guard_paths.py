#!/usr/bin/env python3
"""PreToolUse (Read|Edit|Write|Grep|Glob|NotebookEdit): path policy.

Deny: secrets, env files, presenter-only notes. Ask: edits to the guardrails
themselves. Deny: writes outside the project.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from common import ask, deny, project_dir, read_input

PRESENTER_ONLY = {"DEMO_IDEA.md", "IMPLEMENTATION_PLAN.md"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
CONTROL_PATHS = (
    ".claude/settings.json",
    ".claude/hooks/",
    ".github/workflows/",
    ".github/CODEOWNERS",
)


def candidate_paths(tool_input: dict) -> list[str]:
    keys = ("file_path", "path", "notebook_path")
    return [str(tool_input[k]) for k in keys if tool_input.get(k)]


def main() -> None:
    data = read_input()
    tool = data.get("tool_name", "")
    root = project_dir()
    for raw in candidate_paths(data.get("tool_input", {})):
        p = Path(raw)
        p = (p if p.is_absolute() else root / p).resolve()
        parts = p.parts
        name = p.name
        if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
            deny("PreToolUse", "no-env-files", "env files are off limits.", tool, str(p))
        if "secrets" in parts:
            deny(
                "PreToolUse",
                "no-secrets-dir",
                "the secrets/ directory is off limits.",
                tool,
                str(p),
            )
        if name in PRESENTER_ONLY:
            deny("PreToolUse", "presenter-only", f"{name} is presenter-only.", tool, str(p))
        inside = root == p or root in p.parents
        if tool in WRITE_TOOLS:
            tmp = Path(tempfile.gettempdir()).resolve()
            if not inside and tmp not in p.parents:
                deny(
                    "PreToolUse",
                    "write-outside-project",
                    "writes must stay in the project.",
                    tool,
                    str(p),
                )
            rel = os.path.relpath(p, root) if inside else ""
            if any(rel == c or rel.startswith(c) for c in CONTROL_PATHS):
                ask(
                    "PreToolUse",
                    "protect-guardrails",
                    f"{rel} defines the guardrails; a human must approve changes.",
                    tool,
                    rel,
                )


if __name__ == "__main__":
    main()
