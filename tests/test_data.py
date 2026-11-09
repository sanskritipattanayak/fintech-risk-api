import re
from decimal import Decimal
from pathlib import Path

from app.model import CSV_COLUMNS, read_csv

CSV = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"


def test_csv_exists_with_5000_rows_and_schema() -> None:
    df = read_csv(CSV)
    assert len(df) == 5000
    assert list(df.columns) == CSV_COLUMNS


def test_csv_is_synthetic_and_well_formed() -> None:
    df = read_csv(CSV)
    assert df["card_id"].str.fullmatch(r"card_[0-9a-f]{8}").all()
    assert all(Decimal(a) > 0 for a in df["amount"])
    assert df["timestamp"].str.endswith("+00:00").all()  # tz-aware UTC
    assert df[["card_id", "timestamp", "amount"]].notna().all().all()


def test_csv_has_no_pan_like_numbers_or_emails() -> None:
    text = CSV.read_text()
    assert not re.search(r"\b\d{13,19}\b", text)
    assert "@" not in text
