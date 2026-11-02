"""Guarded release of reservations removed at the source (IPAM-034)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from ipam.extensions import db
from ipam.models import Host, Network

AUTH = {"Authorization": "Bearer test-token"}
SOURCE = "udm-reservations"
LEASE_SOURCE = "udm-leases"
MAC = "aa:bb:cc:dd:ee:01"


def iso(hours):
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def create_reservation(client, **overrides):
    body = {
        "ip_address": "10.9.1.10",
        "mac_address": MAC,
        "hostname": "printer",
        "cname": "print",
        "description": "Office printer",
        "assignment_type": "reservation",
        "assignment_source": SOURCE,
        "assignment_last_confirmed_at": iso(-3),
        "discovery_source": SOURCE,
        **overrides,
    }
    response = client.post("/api/v1/hosts/upsert", headers=AUTH, json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture
def reservation(client):
    return create_reservation(client)


def lease(**overrides):
    return {
        "mac_address": MAC,
        "lease_expires_at": iso(2),
        "lease_source": LEASE_SOURCE,
        "lease_observed_at": iso(0),
        **overrides,
    }


def release(client, snapshot, action, **overrides):
    body = {"source": SOURCE, "action": action, "expected": snapshot}
    body.update(overrides)
    return client.post(
        f"/api/v1/hosts/{snapshot['id']}/release-reservation",
        headers=AUTH,
        json=body,
    )


def stored(client, snapshot):
    return client.get(f"/api/v1/hosts/{snapshot['id']}", headers=AUTH)


def edit_host(snapshot, **values):
    db.session.execute(
        update(Host).where(Host.id == snapshot["id"]).values(values)
    )
    db.session.commit()


class TestDelete:
    def test_deletes_matching_reservation(self, client, reservation):
        assert release(client, reservation, "delete").status_code == 204
        assert stored(client, reservation).status_code == 404
        assert release(client, reservation, "delete").status_code == 404

    def test_refuses_while_stored_lease_is_valid(self, client):
        snapshot = create_reservation(
            client,
            lease_expires_at=iso(1),
            lease_source=LEASE_SOURCE,
            lease_observed_at=iso(-1),
        )
        response = release(client, snapshot, "delete")
        assert response.status_code == 409
        assert "convert" in response.get_json()["message"]
        assert stored(client, snapshot).status_code == 200

    def test_allows_expired_stored_lease(self, client):
        snapshot = create_reservation(
            client,
            lease_expires_at=iso(-1),
            lease_source=LEASE_SOURCE,
            lease_observed_at=iso(-2),
        )
        assert release(client, snapshot, "delete").status_code == 204

    def test_changed_record_is_not_deleted(self, app, client, reservation):
        with app.app_context():
            edit_host(reservation, description="edited after read")

        assert release(client, reservation, "delete").status_code == 412
        assert stored(client, reservation).status_code == 200


class TestGuards:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"assignment_type": "static"},
            {"assignment_source": "manual"},
        ],
    )
    def test_refuses_non_owned_reservations(self, client, overrides):
        snapshot = create_reservation(client, **overrides)
        for action, extra in (("delete", {}), ("convert", {"lease": lease()})):
            response = release(client, snapshot, action, **extra)
            assert response.status_code == 409
        assert stored(client, snapshot).status_code == 200

    @pytest.mark.parametrize(
        "action,overrides",
        [
            ("drop", {}),
            ("delete", {"source": ""}),
            ("delete", {"expected": {"id": 1}}),
            ("convert", {}),
            ("convert", {"lease": lease(mac_address="not-a-mac")}),
            ("convert", {"lease": lease(lease_source=None)}),
            ("convert", {"lease": lease(lease_observed_at=iso(1))}),
            ("convert", {"lease": lease(lease_expires_at="2026-01-01T00:00")}),
            ("convert", {"lease": lease(hostname=42)}),
        ],
    )
    def test_rejects_invalid_requests(
        self, client, reservation, action, overrides
    ):
        response = release(client, reservation, action, **overrides)
        assert response.status_code == 400
        assert stored(client, reservation).get_json() == reservation

    def test_expected_id_must_match_url(self, client, reservation):
        other = create_reservation(
            client, ip_address="10.9.1.11", mac_address="aa:bb:cc:dd:ee:02"
        )
        response = client.post(
            f"/api/v1/hosts/{other['id']}/release-reservation",
            headers=AUTH,
            json={
                "source": SOURCE,
                "action": "delete",
                "expected": reservation,
            },
        )
        assert response.status_code == 400

    def test_requires_api_token(self, client, reservation):
        response = client.post(
            f"/api/v1/hosts/{reservation['id']}/release-reservation",
            json={
                "source": SOURCE,
                "action": "delete",
                "expected": reservation,
            },
        )
        assert response.status_code == 401


class TestConvert:
    def test_same_device_keeps_metadata(self, app, client):
        snapshot = create_reservation(
            client, last_seen=iso(-1), last_seen_source="arp"
        )
        response = release(
            client, snapshot, "convert", lease=lease(hostname="printer-2")
        )
        assert response.status_code == 200
        host = response.get_json()

        assert host["assignment_type"] == "dynamic"
        assert host["assignment_source"] == LEASE_SOURCE
        assert host["discovery_source"] == LEASE_SOURCE
        assert host["is_assigned"] is False
        assert host["lease_source"] == LEASE_SOURCE
        assert host["lease_active"] is True
        assert host["allocation_state"] == "dynamic"
        assert host["hostname"] == "printer-2"
        # Curated and same-device data survives.
        assert host["cname"] == "print"
        assert host["description"] == "Office printer"
        assert host["last_seen_source"] == "arp"
        assert host["last_seen"] == snapshot["last_seen"]
        assert stored(client, snapshot).get_json() == host

    def test_hostname_unchanged_when_lease_has_none(self, client, reservation):
        host = release(client, reservation, "convert", lease=lease()).get_json()
        assert host["hostname"] == "printer"

    def test_new_device_replaces_identity(self, client):
        snapshot = create_reservation(
            client, last_seen=iso(-1), last_seen_source="arp"
        )
        host = release(
            client,
            snapshot,
            "convert",
            lease=lease(mac_address="AA-BB-CC-DD-EE-99"),
        ).get_json()

        assert host["mac_address"] == "aa:bb:cc:dd:ee:99"
        assert host["hostname"] is None
        assert host["last_seen"] is None
        assert host["last_seen_source"] is None
        assert host["cname"] == "print"
        assert host["description"] == "Office printer"

    def test_strips_network_domain_from_hostname(self, app, client):
        with app.app_context():
            network = Network(network="10.9.2.0", cidr=24, domain="lan.test")
            db.session.add(network)
            db.session.commit()
        snapshot = create_reservation(client, ip_address="10.9.2.5")
        assert snapshot["network_id"] is not None

        host = release(
            client,
            snapshot,
            "convert",
            lease=lease(hostname="printer.lan.test"),
        ).get_json()
        assert host["hostname"] == "printer"

    def test_refuses_expired_lease(self, client, reservation):
        response = release(
            client,
            reservation,
            "convert",
            lease=lease(lease_expires_at=iso(-1), lease_observed_at=iso(-2)),
        )
        assert response.status_code == 409
        assert "delete" in response.get_json()["message"]

    def test_refuses_older_observation(self, client):
        snapshot = create_reservation(
            client,
            lease_expires_at=iso(1),
            lease_source=LEASE_SOURCE,
            lease_observed_at=iso(-1),
        )
        response = release(
            client,
            snapshot,
            "convert",
            lease=lease(lease_observed_at=iso(-2)),
        )
        assert response.status_code == 409
        assert stored(client, snapshot).get_json() == snapshot

    def test_changed_record_is_not_converted(self, app, client, reservation):
        with app.app_context():
            edit_host(reservation, mac_address="aa:bb:cc:dd:ee:55")

        response = release(client, reservation, "convert", lease=lease())
        assert response.status_code == 412
        host = stored(client, reservation).get_json()
        assert host["assignment_type"] == "reservation"
        assert host["mac_address"] == "aa:bb:cc:dd:ee:55"

    def test_converted_host_can_later_be_retired(self, app, client):
        """The converted record fits the dynamic retirement contract."""
        snapshot = create_reservation(client, cname=None, description=None)
        host = release(
            client,
            snapshot,
            "convert",
            lease=lease(lease_observed_at=iso(-0.5)),
        ).get_json()

        app.config["LEASE_RETIRE_MIN_AGE_SECONDS"] = 0
        with app.app_context():
            edit_host(
                host,
                lease_expires_at=datetime.now(UTC).replace(tzinfo=None)
                - timedelta(minutes=5),
            )
        expired = stored(client, host).get_json()
        response = client.post(
            f"/api/v1/hosts/{host['id']}/retire-lease",
            headers=AUTH,
            json={
                "source": LEASE_SOURCE,
                "expired_before": iso(0),
                "expected": expired,
            },
        )
        assert response.status_code == 204, response.get_json()
