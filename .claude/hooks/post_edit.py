#!/usr/bin/env python3
"""PostToolUse (Edit|Write): fintech conventions on the file just written.

1. No restricted data (PAN/SSN/keys) written into any file.
2. Python: ruff (includes naive-datetime rule DTZ), and no float used for money.
Exit code 2 returns the findings to Claude so it fixes them in the same turn.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import dlp
from common import deny, project_dir, read_input

MONEY = re.compile(r"amount|price|balance|limit|fee|total|cost|payment", re.I)
MARKER = "money-float-ok"


def float_for_money(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    problems: list[str] = []

    def mentions_money(node: ast.AST) -> bool:
        return any(
            (isinstance(n, ast.Name) and MONEY.search(n.id))
            or (isinstance(n, ast.Attribute) and MONEY.search(n.attr))
            for n in ast.walk(node)
        )

    def flag(node: ast.AST, why: str) -> None:
        line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
        if MARKER not in line:
            problems.append(f"{path.name}:{node.lineno}: {why}")

    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "float":
            if any(mentions_money(a) for a in node.args):
                flag(node, "float() applied to a money value; use Decimal")
        elif isinstance(node, ast.arg) and node.annotation is not None:
            if MONEY.search(node.arg) and "float" in ast.unparse(node.annotation):
                flag(node, f"money parameter '{node.arg}' annotated float; use Decimal")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if MONEY.search(node.target.id) and "float" in ast.unparse(node.annotation):
                flag(node, f"money variable '{node.target.id}' annotated float; use Decimal")
        elif isinstance(node, ast.Compare):
            parts = [node.left, *node.comparators]
            has_float = any(
                isinstance(p, ast.Constant) and isinstance(p.value, float) for p in parts
            )
            if has_float and mentions_money(node):
                flag(node, "money compared with a float literal; use Decimal")
    return problems


def main() -> None:
    data = read_input()
    raw = data.get("tool_input", {}).get("file_path")
    if not raw:
        return
    root = project_dir()
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    findings = dlp.scan_text(text)
    if findings:
        deny(
            "PostToolUse",
            "write-dlp",
            f"{path.name} now contains restricted data ({dlp.summarize(findings)}). "
            "Remove it and use synthetic tokens.",
            "Write",
            str(path),
        )
    if path.suffix != ".py":
        return
    problems = float_for_money(path)
    ruff = root / ".venv" / "bin" / "ruff"
    exe = str(ruff) if ruff.exists() else shutil.which("ruff")
    if exe:
        r = subprocess.run(
            [exe, "check", "--no-fix", "--output-format=concise", str(path)],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if r.returncode != 0:
            problems += r.stdout.strip().splitlines()
    if problems:
        deny(
            "PostToolUse",
            "post-edit-lint",
            "fix these before continuing:\n" + "\n".join(problems),
            "Edit",
            str(path),
        )


if __name__ == "__main__":
    main()
