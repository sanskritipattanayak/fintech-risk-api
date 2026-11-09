#!/usr/bin/env python3
"""PreToolUse (Bash): command policy.

Deny exfiltration, secret access, pushes to main, force pushes, merges.
Ask for installs, deletions and history rewrites.
On `git commit`: secret/PII scan of the staged diff and a green test run.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from common import ask, deny, project_dir, read_input

HERE = os.path.dirname(os.path.abspath(__file__))
NETWORK = re.compile(r"(?:^|[\s;&|(])(curl|wget|nc|ncat|telnet|ssh|scp|sftp|ftp)\s")
ENV_ACCESS = re.compile(r"(?:^|[\s/='\"])\.env(?:\.[\w-]+)?(?=$|[\s;&|'\"])")
SECRETS = re.compile(r"(?:^|[\s/='\"])secrets/")
PRESENTER = re.compile(r"DEMO_IDEA\.md|IMPLEMENTATION_PLAN\.md")
INSTALL = re.compile(r"\b(?:pip3?|uv pip|npm|pnpm|yarn|brew|apt(?:-get)?)\s+install\b")
FORCE = re.compile(r"git\s+push\b.*(?:\s--force\b|\s--force-with-lease\b|\s-f\b)")
PUSH_MAIN = re.compile(r"git\s+push\b[^;&|]*?(?:\s|:)(?:main|master)\b")
HISTORY = re.compile(
    r"git\s+(?:reset\s+--hard|rebase|filter-branch|clean\s+-\w*f|commit\s+--amend)"
)
MERGE = re.compile(r"gh\s+pr\s+merge|--auto\b.*merge|gh\s+api\b.*merge")
RM_RECURSIVE = re.compile(r"\brm\s+(?:-\w*[rR]\w*|-\w*f\w*[rR]\w*)")
RM_ANY = re.compile(r"(?:^|[\s;&|(])rm\s")


def current_branch() -> str:
    out = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True, cwd=project_dir()
    )
    return out.stdout.strip()


def commit_gate(cmd: str) -> None:
    root = project_dir()
    scan = subprocess.run(
        [sys.executable, os.path.join(HERE, "dlp.py"), "staged"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if scan.returncode != 0:
        deny(
            "PreToolUse",
            "commit-dlp",
            "staged changes contain restricted data or secrets. Remove or tokenise them.\n"
            + scan.stdout.strip(),
            "Bash",
            cmd,
        )
    py = root / ".venv" / "bin" / "python"
    tests = subprocess.run(
        [str(py if py.exists() else sys.executable), "-m", "pytest", "-q", "-x"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if tests.returncode != 0:
        tail = "\n".join(tests.stdout.strip().splitlines()[-15:])
        deny("PreToolUse", "commit-tests", "tests must pass before commit.\n" + tail, "Bash", cmd)


def main() -> None:
    data = read_input()
    if data.get("tool_name") != "Bash":
        return
    cmd = data.get("tool_input", {}).get("command", "")
    ev, tool = "PreToolUse", "Bash"

    if NETWORK.search(cmd):
        deny(ev, "no-network", "network tools are blocked (no exfiltration path).", tool, cmd)
    if ENV_ACCESS.search(cmd) or SECRETS.search(cmd):
        deny(ev, "no-secret-access", "env files and secrets/ are off limits.", tool, cmd)
    if PRESENTER.search(cmd):
        deny(ev, "presenter-only", "presenter-only notes are off limits.", tool, cmd)
    if MERGE.search(cmd):
        deny(ev, "no-merge", "Claude never merges; a human reviews and merges.", tool, cmd)
    if FORCE.search(cmd):
        deny(ev, "no-force-push", "force pushes are blocked.", tool, cmd)
    if PUSH_MAIN.search(cmd):
        deny(ev, "no-push-main", "push to a feature or fix branch and open a PR.", tool, cmd)
    if re.search(r"git\s+push\b", cmd) and current_branch() in {"main", "master"}:
        deny(ev, "no-push-main", "you are on main; use a feature branch and a PR.", tool, cmd)
    if RM_RECURSIVE.search(cmd):
        deny(ev, "no-recursive-delete", "recursive deletes are blocked; ask the human.", tool, cmd)
    if HISTORY.search(cmd):
        ask(ev, "history-rewrite", "this rewrites history or discards work.", tool, cmd)
    if RM_ANY.search(cmd):
        ask(ev, "delete-files", "deleting files needs human approval.", tool, cmd)
    if INSTALL.search(cmd):
        ask(ev, "package-install", "installs reach a package index; approve it.", tool, cmd)
    if re.search(r"git\s+commit\b", cmd):
        commit_gate(cmd)


if __name__ == "__main__":
    main()
