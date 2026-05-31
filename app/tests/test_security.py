from __future__ import annotations


def _token(client, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_missing_jwt_returns_401(client):
    response = client.get("/api/v1/datasets")
    assert response.status_code == 401


def test_invalid_jwt_returns_401(client):
    response = client.get("/api/v1/datasets", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_insufficient_scope_returns_403(client):
    reader = _token(client, "reader", "reader")
    response = client.post(
        "/api/v1/generation/jobs",
        json={"record_count": 10, "enable_llm_enrichment": False, "dataset_version": "vsec001"},
        headers={"Authorization": f"Bearer {reader}"},
    )
    assert response.status_code == 403
