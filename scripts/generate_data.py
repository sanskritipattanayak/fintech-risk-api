"""Regenerate data/transactions.csv (synthetic only). Usage: python scripts/generate_data.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.model import generate_transactions, write_csv  # noqa: E402

if __name__ == "__main__":
    out = ROOT / "data" / "transactions.csv"
    write_csv(generate_transactions(5000, seed=42), out)
    print(f"wrote {out}")
