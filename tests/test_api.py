from fastapi.testclient import TestClient

BASE = {
    "card_id": "card_0a1b2c3d",
    "amount": "25.50",
    "timestamp": "2026-03-01T12:00:00Z",
    "merchant_category": "grocery",
    "card_age_days": 900,
}


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_score_approves_ordinary_transaction(client: TestClient) -> None:
    r = client.post("/score", json=BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "APPROVED"
    assert 0.0 <= body["risk_score"] <= 1.0


def test_velocity_decline_after_burst(client: TestClient) -> None:
    decisions = [client.post("/score", json=BASE).json()["decision"] for _ in range(7)]
    assert decisions[:5] == ["APPROVED"] * 5
    assert decisions[5:] == ["DECLINED_VELOCITY"] * 2


def test_naive_timestamp_rejected(client: TestClient) -> None:
    r = client.post("/score", json={**BASE, "timestamp": "2026-03-01T12:00:00"})
    assert r.status_code == 422


def test_bad_card_id_rejected(client: TestClient) -> None:
    # A PAN-like value must never be accepted as a card identifier.
    r = client.post("/score", json={**BASE, "card_id": "4111111111111111"})
    assert r.status_code == 422


def test_non_positive_and_excess_precision_amounts_rejected(client: TestClient) -> None:
    assert client.post("/score", json={**BASE, "amount": "0"}).status_code == 422
    assert client.post("/score", json={**BASE, "amount": "-5.00"}).status_code == 422
    assert client.post("/score", json={**BASE, "amount": "1.234"}).status_code == 422
