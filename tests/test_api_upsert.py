"""Tests for the network, host, and DHCP range upsert API endpoints."""

AUTH = {"Authorization": "Bearer test-token"}


def test_upsert_network_creates_and_updates(client):
    create = client.post(
        "/api/v1/networks/upsert",
        json={
            "network": "10.0.1.0",
            "cidr": 24,
            "name": "Old Name",
            "location": "Office",
        },
        headers=AUTH,
    )
    assert create.status_code == 201
    created = create.get_json()
    assert created["name"] == "Old Name"
    assert created["location"] == "Office"

    update = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.1.0", "cidr": 24, "name": "New Name"},
        headers=AUTH,
    )
    assert update.status_code == 200
    updated = update.get_json()
    assert updated["id"] == created["id"]
    assert updated["name"] == "New Name"
    # location was omitted from the update body -> must be preserved
    assert updated["location"] == "Office"


def test_upsert_network_explicit_null_clears_field(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.2.0", "cidr": 24, "location": "Office"},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.2.0", "cidr": 24, "location": None},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.get_json()["location"] is None


def test_upsert_network_requires_network_and_cidr(client):
    response = client.post(
        "/api/v1/networks/upsert", json={"network": "10.0.3.0"}, headers=AUTH
    )
    assert response.status_code == 400


def test_upsert_host_creates_and_updates(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.1.0", "cidr": 24},
        headers=AUTH,
    )

    create = client.post(
        "/api/v1/hosts/upsert",
        json={
            "ip_address": "10.0.1.5",
            "hostname": "old-name",
            "cname": "manually-set-cname",
            "description": "manually curated note",
        },
        headers=AUTH,
    )
    assert create.status_code == 201
    created = create.get_json()
    assert created["hostname"] == "old-name"
    assert created["cname"] == "manually-set-cname"
    # network auto-detected from the IP since network_id was omitted
    assert created["network"] == "10.0.1.0/24"

    update = client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.5", "hostname": "new-name"},
        headers=AUTH,
    )
    assert update.status_code == 200
    updated = update.get_json()
    assert updated["id"] == created["id"]
    assert updated["hostname"] == "new-name"
    # cname/description were omitted from the update -> preserved
    assert updated["cname"] == "manually-set-cname"
    assert updated["description"] == "manually curated note"


def test_upsert_host_explicit_null_clears_field(client):
    client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.9", "cname": "temp-cname"},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.9", "cname": None},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.get_json()["cname"] is None


def test_upsert_host_requires_ip_address(client):
    response = client.post(
        "/api/v1/hosts/upsert", json={"hostname": "no-ip"}, headers=AUTH
    )
    assert response.status_code == 400


def test_upsert_host_is_assigned_default_on_create(client):
    response = client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.20"},
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["is_assigned"] is True


def test_upsert_host_preserves_is_assigned_when_omitted(client):
    client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.21", "is_assigned": False},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/hosts/upsert",
        json={"ip_address": "10.0.1.21", "hostname": "still-unassigned"},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.get_json()["is_assigned"] is False


def test_upsert_dhcp_range_creates_and_updates(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.3.0", "cidr": 24},
        headers=AUTH,
    )

    create = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={
            "network_id": 1,
            "start_ip": "10.0.3.100",
            "end_ip": "10.0.3.150",
            "description": "Office pool",
        },
        headers=AUTH,
    )
    assert create.status_code == 201
    created = create.get_json()
    assert created["end_ip"] == "10.0.3.150"
    assert created["description"] == "Office pool"

    update = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={
            "network_id": 1,
            "start_ip": "10.0.3.100",
            "end_ip": "10.0.3.200",
        },
        headers=AUTH,
    )
    assert update.status_code == 200
    updated = update.get_json()
    assert updated["id"] == created["id"]
    assert updated["end_ip"] == "10.0.3.200"
    # description was omitted from the update -> preserved
    assert updated["description"] == "Office pool"


def test_upsert_dhcp_range_auto_detects_network(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.4.0", "cidr": 24},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={"start_ip": "10.0.4.100", "end_ip": "10.0.4.150"},
        headers=AUTH,
    )

    assert response.status_code == 201
    assert response.get_json()["network_id"] == 1


def test_upsert_dhcp_range_no_matching_network(client):
    response = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={"start_ip": "192.168.99.100", "end_ip": "192.168.99.150"},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_upsert_dhcp_range_requires_start_and_end_ip(client):
    response = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={"network_id": 1},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_upsert_dhcp_range_explicit_null_clears_description(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.6.0", "cidr": 24},
        headers=AUTH,
    )
    client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={
            "network_id": 1,
            "start_ip": "10.0.6.100",
            "end_ip": "10.0.6.150",
            "description": "temp",
        },
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={
            "network_id": 1,
            "start_ip": "10.0.6.100",
            "end_ip": "10.0.6.150",
            "description": None,
        },
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.get_json()["description"] is None


def test_upsert_dhcp_range_rejects_range_outside_network(client):
    client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.0.7.0", "cidr": 24},
        headers=AUTH,
    )

    response = client.post(
        "/api/v1/dhcp-ranges/upsert",
        json={
            "network_id": 1,
            "start_ip": "10.0.8.100",
            "end_ip": "10.0.8.150",
        },
        headers=AUTH,
    )

    assert response.status_code == 400


def test_upsert_host_serializes_last_seen(client):
    """Regression test: the response must be marshaled (not a raw dict),
    otherwise a datetime value in last_seen fails JSON serialization."""
    response = client.post(
        "/api/v1/hosts/upsert",
        json={
            "ip_address": "10.0.1.22",
            "last_seen": "2025-12-28T10:01:58Z",
        },
        headers=AUTH,
    )

    assert response.status_code == 201
    assert response.get_json()["last_seen"] == "2025-12-28T10:01:58"
