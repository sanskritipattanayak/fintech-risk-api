import pytest
from fastapi.testclient import TestClient

from app import main
from app.velocity import VelocityChecker


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "velocity", VelocityChecker())  # fresh state per test
    return TestClient(main.app)
