"""Canary tests: planted fake sensitive data must be caught wherever it appears."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "hooks"))
import dlp  # noqa: E402

from tests.canary import canaries  # noqa: E402

LOCATIONS = {
    "prd": canaries.PRD_TEXT,
    "log": canaries.LOG_LINE,
    "fixture": canaries.FIXTURE_ROW,
    "diff": canaries.DIFF_ADDED,
}


@pytest.mark.parametrize("kind,value", canaries.ALL.items())
def test_each_canary_detected(kind: str, value: str) -> None:
    assert kind in {f.kind for f in dlp.scan_text(f"note: {value} end")}


def test_spaced_pan_detected() -> None:
    assert "pan" in {f.kind for f in dlp.scan_text(canaries.PAN_SPACED)}


@pytest.mark.parametrize("where,text", LOCATIONS.items())
def test_canary_detected_in_every_location(where: str, text: str) -> None:
    assert dlp.scan_text(text), f"canary missed in {where}: detector is broken"


@pytest.mark.parametrize("where,text", LOCATIONS.items())
def test_redaction_removes_canaries(where: str, text: str) -> None:
    out = dlp.redact(text)
    for value in canaries.ALL.values():
        assert value not in out, f"{value[:4]}... survived redaction in {where}"
    assert "[REDACTED:" in out


def test_findings_never_contain_the_value() -> None:
    for f in dlp.scan_text(canaries.PRD_TEXT):
        for value in canaries.ALL.values():
            assert value not in repr(f)


def test_benign_synthetic_data_is_not_flagged() -> None:
    benign = (
        "card_0a1b2c3d,2026-03-01T12:00:00+00:00,25.50,USD\n"
        "txn_000123 epoch 1700000000000 order 1234567890123456\n"
        "contact ops@example.test or noreply@anthropic.com\n"
    )
    assert dlp.scan_text(benign) == []


def test_repository_data_files_are_clean() -> None:
    root = Path(__file__).resolve().parents[2]
    assert dlp.scan_text((root / "data" / "transactions.csv").read_text()) == []
