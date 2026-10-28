from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_rulebooks_endpoint():
    response = client.get("/api/rulebooks")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 3
    assert any(item["category"] == "documents" for item in body)
