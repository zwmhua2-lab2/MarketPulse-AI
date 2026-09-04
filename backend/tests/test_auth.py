from fastapi.testclient import TestClient
from marketpulse.api.app import app


def test_protected_endpoint_requires_session():
    response = TestClient(app).get("/api/v1/protected/ping")
    assert response.status_code == 401


def test_login_then_protected_endpoint():
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "dev-only-change-this-password"})
    assert login.status_code == 200
    response = client.get("/api/v1/protected/ping", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert response.status_code == 200

