from __future__ import annotations


def _create_dataset(client, auth_headers, version: str = "vapi001") -> str:
    response = client.post(
        "/api/v1/generation/jobs",
        json={"record_count": 20, "enable_llm_enrichment": False, "dataset_version": version},
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()["dataset_version"]


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_pagination_and_filters(client, auth_headers):
    dataset_version = _create_dataset(client, auth_headers, "vapi002")
    flights = client.get(
        f"/api/v1/flights?dataset_version={dataset_version}&page=1&page_size=5&origin=MAA",
        headers=auth_headers,
    )
    assert flights.status_code == 200
    body = flights.json()
    assert body["page_size"] == 5
    assert len(body["items"]) <= 5
    assert all(row["origin"] == "MAA" for row in body["items"])


def test_invalid_ids_return_404(client, auth_headers):
    _create_dataset(client, auth_headers, "vapi003")
    assert client.get("/api/v1/bookings/XXXXXX", headers=auth_headers).status_code == 404
    assert client.get("/api/v1/flights/INVALID-FLT", headers=auth_headers).status_code == 404
