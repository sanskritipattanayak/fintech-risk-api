#!/usr/bin/env python3
"""DLP detector shared by every guardrail (prompt hook, commit gate, CI, tests).

Stdlib only. Never returns or prints the matched value: findings carry the kind,
position and a short hash so a human can correlate without the data being copied
into logs, prompts or terminal output.

CLI:
  dlp.py scan FILE...        scan files, exit 1 on findings
  dlp.py staged              scan added lines of `git diff --cached`
  dlp.py worktree            scan staged + unstaged changes + untracked files
  dlp.py range [BASE]        scan commits in BASE...HEAD (default origin/main)
  dlp.py tracked             scan every git-tracked text file
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass

ALLOWED_EMAIL_DOMAINS = {"example.test", "example.com", "example.org"}
ALLOWED_EMAILS = {"noreply@anthropic.com"}

PAN_RE = re.compile(r"(?<![\w.])(?:\d[ -]?){12,18}\d(?![\w])")
SSN_RE = re.compile(r"(?<!\d)(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?!\d)")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
PATTERNS = {
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    "private_key": re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    "secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b[\"']?\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9_\-/+=]{16,}"
    ),
}


@dataclass(frozen=True)
class Finding:
    kind: str
    line: int
    start: int
    end: int
    digest: str  # short sha256 of the matched value, never the value itself


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def iban_ok(value: str) -> bool:
    rearranged = value[4:] + value[:4]
    num = "".join(str(int(c, 36)) for c in rearranged)
    return int(num) % 97 == 1


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def scan_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in PAN_RE.finditer(line):
            digits = re.sub(r"\D", "", m.group())
            if 13 <= len(digits) <= 19 and digits[0] in "3456" and luhn_ok(digits):
                findings.append(Finding("pan", lineno, m.start(), m.end(), _digest(digits)))
        for m in SSN_RE.finditer(line):
            findings.append(Finding("ssn", lineno, m.start(), m.end(), _digest(m.group())))
        for m in IBAN_RE.finditer(line):
            if iban_ok(m.group()):
                findings.append(Finding("iban", lineno, m.start(), m.end(), _digest(m.group())))
        for m in EMAIL_RE.finditer(line):
            domain = m.group(1).lower()
            if domain not in ALLOWED_EMAIL_DOMAINS and m.group().lower() not in ALLOWED_EMAILS:
                findings.append(Finding("email", lineno, m.start(), m.end(), _digest(m.group())))
        for kind, rx in PATTERNS.items():
            for m in rx.finditer(line):
                findings.append(Finding(kind, lineno, m.start(), m.end(), _digest(m.group())))
    return findings


def redact(text: str) -> str:
    """Replace every finding with ``[REDACTED:kind]`` (used before log analysis)."""
    out_lines = []
    for line in text.splitlines():
        spans = sorted(
            ((f.start, f.end, f.kind) for f in scan_text(line) if f.line == 1), reverse=True
        )
        for start, end, kind in spans:
            line = line[:start] + f"[REDACTED:{kind}]" + line[end:]
        out_lines.append(line)
    return "\n".join(out_lines)


def summarize(findings: list[Finding]) -> str:
    kinds: dict[str, int] = {}
    for f in findings:
        kinds[f.kind] = kinds.get(f.kind, 0) + 1
    return ", ".join(f"{k} x{n}" for k, n in sorted(kinds.items()))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def _report(label: str, findings: list[Finding]) -> int:
    for f in findings:
        print(f"{label}:{f.line}: {f.kind} [{f.digest}]")
    return 1 if findings else 0


def _scan_diff(diff: str) -> int:
    """Scan only the added lines of a unified diff, grouped by file."""
    current = ""
    added: dict[str, list[str]] = {}
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added.setdefault(current, []).append(line[1:])
    rc = 0
    for path, lines in added.items():
        rc |= _report(path, scan_text("\n".join(lines)))
    return rc


def _scan_file(path: str) -> int:
    try:
        text = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return 0
    return _report(path, scan_text(text))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    rc = 0
    if cmd == "scan":
        for path in argv[2:]:
            try:
                text = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            rc |= _report(path, scan_text(text))
    elif cmd == "staged":
        rc |= _scan_diff(_git("diff", "--cached", "-U0", "--no-color"))
    elif cmd == "worktree":
        # Everything a commit could pick up: staged + unstaged changes + untracked files.
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, check=False
        )
        diff_args = ["diff", "HEAD"] if head.returncode == 0 else ["diff", "--cached"]
        rc |= _scan_diff(_git(*diff_args, "-U0", "--no-color"))
        for path in _git("ls-files", "--others", "--exclude-standard").splitlines():
            rc |= _scan_file(path)
    elif cmd == "range":
        # Commits that would leave the machine: BASE...HEAD (default origin/main).
        base = argv[2] if len(argv) > 2 else "origin/main"
        ok = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", base], capture_output=True, check=False
        )
        if ok.returncode != 0:
            print(f"range: base '{base}' not found; scanning all tracked files", file=sys.stderr)
            for path in _git("ls-files").splitlines():
                rc |= _scan_file(path)
        else:
            rc |= _scan_diff(_git("diff", f"{base}...HEAD", "-U0", "--no-color"))
    elif cmd == "tracked":
        for path in _git("ls-files").splitlines():
            try:
                text = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            rc |= _report(path, scan_text(text))
    else:
        print(__doc__)
        return 2
    print("DATA_CHECK: FAIL" if rc else "DATA_CHECK: PASS")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
