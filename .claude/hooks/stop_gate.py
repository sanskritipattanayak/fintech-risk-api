#!/usr/bin/env python3
"""Stop: Claude may not declare "done" while the test suite is red."""

from __future__ import annotations

import subprocess
import sys

from common import deny, project_dir, read_input


def main() -> None:
    data = read_input()
    root = project_dir()
    if not (root / "tests").is_dir():
        return
    py = root / ".venv" / "bin" / "python"
    r = subprocess.run(
        [str(py if py.exists() else sys.executable), "-m", "pytest", "-q", "-x"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        return
    tail = "\n".join(r.stdout.strip().splitlines()[-15:])
    if data.get("stop_hook_active"):
        # Already forced one continuation; do not loop forever. Surface it instead.
        print("WARNING: tests still failing after retry.\n" + tail, file=sys.stderr)
        return
    deny("Stop", "stop-red-tests", "tests are failing; fix them before finishing.\n" + tail, "Stop")


if __name__ == "__main__":
    main()
