from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_claims_endpoint():
    response = client.get("/api/claims")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["id"].startswith("CLM-")


def test_single_claim_endpoint():
    response = client.get("/api/claims/CLM-3021")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "Health Insurance"
    assert "analysis" in body
