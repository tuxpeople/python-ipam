"""Regression tests: network address normalization, hostname domain
suffix stripping, and CIDR-change protection, applied consistently
across POST, PUT, and upsert -- these previously only worked through
the CSV/JSON import flow.
"""

AUTH = {"Authorization": "Bearer test-token"}


# --- Network address normalization -----------------------------------


def test_post_network_normalizes_host_ip(client):
    response = client.post(
        "/api/v1/networks",
        json={"network": "10.30.1.42", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["network"] == "10.30.1.0"
    assert body["broadcast_address"] == "10.30.1.255"


def test_put_network_normalizes_host_ip(client):
    created = client.post(
        "/api/v1/networks",
        json={"network": "10.30.2.0", "cidr": 24},
        headers=AUTH,
    ).get_json()

    response = client.put(
        f"/api/v1/networks/{created['id']}",
        json={"network": "10.30.2.99", "cidr": 24, "name": "renamed"},
        headers=AUTH,
    )
    assert response.status_code == 200
    assert response.get_json()["network"] == "10.30.2.0"


def test_upsert_network_normalizes_host_ip(client):
    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.30.3.55", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["network"] == "10.30.3.0"


# --- Hostname domain suffix stripping ----------------------------------


def test_post_host_strips_matching_network_domain(client):
    client.post(
        "/api/v1/networks",
        json={"network": "10.31.1.0", "cidr": 24, "domain": "example.com"},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/hosts",
        json={
            "ip_address": "10.31.1.5",
            "hostname": "server01.example.com",
        },
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["hostname"] == "server01"


def test_put_host_strips_matching_network_domain(client):
    client.post(
        "/api/v1/networks",
        json={"network": "10.31.2.0", "cidr": 24, "domain": "example.com"},
        headers=AUTH,
    )
    created = client.post(
        "/api/v1/hosts",
        json={"ip_address": "10.31.2.5", "hostname": "server01"},
        headers=AUTH,
    ).get_json()

    response = client.put(
        f"/api/v1/hosts/{created['id']}",
        json={
            "ip_address": "10.31.2.5",
            "hostname": "server02.example.com",
        },
        headers=AUTH,
    )
    assert response.status_code == 200
    assert response.get_json()["hostname"] == "server02"


def test_upsert_host_strips_matching_network_domain(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.31.3.0", "cidr": 24, "domain": "example.com"},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/hosts/upsert",
        json={
            "ip_address": "10.31.3.5",
            "hostname": "server01.example.com",
        },
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["hostname"] == "server01"


def test_upsert_host_leaves_unmatched_domain_untouched(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.31.4.0", "cidr": 24, "domain": "example.com"},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/hosts/upsert",
        json={
            "ip_address": "10.31.4.5",
            "hostname": "server01.other.com",
        },
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["hostname"] == "server01.other.com"


# --- CIDR-change protection ---------------------------------------------


def test_put_network_rejects_cidr_change(client):
    created = client.post(
        "/api/v1/networks",
        json={"network": "10.32.1.0", "cidr": 24},
        headers=AUTH,
    ).get_json()

    response = client.put(
        f"/api/v1/networks/{created['id']}",
        json={"network": "10.32.1.0", "cidr": 25},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_upsert_network_rejects_cidr_change(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.32.2.0", "cidr": 24},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.32.2.0", "cidr": 25},
        headers=AUTH,
    )
    assert response.status_code == 400


# --- Network overlap rejection -------------------------------------------


def test_post_network_rejects_overlap(client):
    client.post(
        "/api/v1/networks",
        json={"network": "10.33.0.0", "cidr": 16},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/networks",
        json={"network": "10.33.5.0", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_put_network_rejects_overlap(client):
    client.post(
        "/api/v1/networks",
        json={"network": "10.34.0.0", "cidr": 16},
        headers=AUTH,
    )
    movable = client.post(
        "/api/v1/networks",
        json={"network": "10.50.0.0", "cidr": 24},
        headers=AUTH,
    ).get_json()

    response = client.put(
        f"/api/v1/networks/{movable['id']}",
        json={"network": "10.34.5.0", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_upsert_network_rejects_overlap(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.35.0.0", "cidr": 16},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.35.5.0", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_upsert_network_allows_disjoint_networks(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.36.0.0", "cidr": 24},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.37.0.0", "cidr": 24},
        headers=AUTH,
    )
    assert response.status_code == 201
