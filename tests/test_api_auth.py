"""API authentication tests."""


def test_api_requires_token(client):
    response = client.get("/api/v1/networks")
    assert response.status_code == 401


def test_api_accepts_token(client):
    response = client.get(
        "/api/v1/networks", headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200


def test_api_accepts_api_key_header(client):
    response = client.get(
        "/api/v1/networks", headers={"X-API-Key": "test-token"}
    )
    assert response.status_code == 200


def test_api_docs_no_auth(client):
    response = client.get("/api/v1/docs")
    assert response.status_code == 200
