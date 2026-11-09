"""Regenerate logs/app.log from the real decision code (synthetic only).

Usage: python scripts/generate_logs.py [N_EVENTS]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.simulate import simulate, write_log  # noqa: E402

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    out = ROOT / "logs" / "app.log"
    records = simulate(n=n)
    write_log(records, out)
    declines = sum(r["event"] == "DECLINED_VELOCITY" for r in records)
    print(f"wrote {len(records)} events to {out} ({declines} DECLINED_VELOCITY)")
