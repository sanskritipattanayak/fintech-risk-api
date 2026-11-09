from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.velocity import VelocityChecker


@pytest.fixture(autouse=True)
def log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test logs to a temp file, never to the committed logs/app.log."""
    path = tmp_path / "app.log"
    monkeypatch.setenv("RISK_LOG_PATH", str(path))
    return path


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "velocity", VelocityChecker())  # fresh state per test
    return TestClient(main.app)
