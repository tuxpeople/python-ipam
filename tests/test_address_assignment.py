"""Tests for the address assignment, lease and observation model.

Covers the acceptance cases of ADDRESS_ASSIGNMENT_MODEL.md.
"""

import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from ipam.allocation import derive_allocation_state, parse_timestamp
from ipam.extensions import db
from ipam.models import DhcpRange, Host, Network

AUTH = {"Authorization": "Bearer test-token"}


def _iso(dt):
    return dt.astimezone(UTC).isoformat()


def _future(hours=1):
    return _iso(datetime.now(UTC) + timedelta(hours=hours))


def _past(hours=1):
    return _iso(datetime.now(UTC) - timedelta(hours=hours))


def _upsert(client, **body):
    return client.post("/api/v1/hosts/upsert", json=body, headers=AUTH)


@pytest.fixture
def network(client):
    response = client.post(
        "/api/v1/networks/upsert",
        json={"network": "10.9.0.0", "cidr": 24, "domain": "lab.example"},
        headers=AUTH,
    )
    assert response.status_code in (200, 201)
    return response.get_json()


# --- Coexistence and derived state ------------------------------------


def test_reservation_lease_and_observation_coexist(client, network):
    _upsert(
        client,
        ip_address="10.9.0.10",
        mac_address="aa:bb:cc:00:00:10",
        assignment_type="reservation",
        assignment_source="udm-reservations",
        assignment_last_confirmed_at=_past(2),
    )
    _upsert(
        client,
        ip_address="10.9.0.10",
        lease_expires_at=_future(),
        lease_source="udm-leases",
        lease_observed_at=_past(1),
    )
    response = _upsert(
        client,
        ip_address="10.9.0.10",
        last_seen=_past(0.1),
        last_seen_source="ping",
    )

    host = response.get_json()
    assert host["assignment_type"] == "reservation"
    assert host["assignment_source"] == "udm-reservations"
    assert host["lease_source"] == "udm-leases"
    assert host["lease_active"] is True
    assert host["last_seen_source"] == "ping"
    assert host["allocation_state"] == "reserved_lease_active"
    assert host["allocation_label"] == "Reserved; lease active"


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ({"assignment_type": "reservation"}, "reserved"),
        (
            {"assignment_type": "reservation", "lease_expires_at": "future"},
            "reserved_lease_active",
        ),
        ({"lease_expires_at": "future"}, "dynamic"),
        (
            {"assignment_type": "dynamic", "lease_expires_at": "future"},
            "dynamic",
        ),
        ({"assignment_type": "static"}, "static"),
        ({"assignment_type": "static", "last_seen": "past"}, "static"),
        ({"lease_expires_at": "past"}, "lease_expired"),
        (
            {"assignment_type": "dynamic", "lease_expires_at": "past"},
            "lease_expired",
        ),
        ({"last_seen": "past"}, "observed"),
        ({}, "unknown"),
        ({"assignment_type": "unknown"}, "unknown"),
    ],
)
def test_derived_allocation_state(facts, expected):
    now = datetime(2026, 10, 31, 12, 0)
    host = Host(ip_address="10.9.0.1")
    for field, value in facts.items():
        if value == "future":
            value = now + timedelta(hours=1)
        elif value == "past":
            value = now - timedelta(hours=1)
        setattr(host, field, value)
    assert derive_allocation_state(host, now=now) == expected


def test_no_record_state():
    assert derive_allocation_state(None) == "no_record"


# --- Persistence -------------------------------------------------------


def test_reservation_survives_lease_expiry_and_offline(client, network):
    _upsert(client, ip_address="10.9.0.11", assignment_type="reservation")
    response = _upsert(
        client,
        ip_address="10.9.0.11",
        lease_expires_at=_past(1),
        lease_observed_at=_past(2),
        last_seen=_past(48),
    )
    host = response.get_json()
    assert host["assignment_type"] == "reservation"
    assert host["lease_active"] is False
    assert host["allocation_state"] == "reserved"


def test_static_assignment_survives_missed_observations(client, network):
    _upsert(client, ip_address="10.9.0.12", assignment_type="static")
    response = _upsert(client, ip_address="10.9.0.12", last_seen=_past(24 * 30))
    assert response.get_json()["allocation_state"] == "static"


@pytest.mark.parametrize("persistent", ["reservation", "static"])
@pytest.mark.parametrize("weaker", ["dynamic", "unknown"])
def test_lease_collector_does_not_downgrade_persistent_assignment(
    client, network, persistent, weaker
):
    _upsert(client, ip_address="10.9.0.13", assignment_type=persistent)
    response = _upsert(
        client,
        ip_address="10.9.0.13",
        assignment_type=weaker,
        assignment_source="udm-leases",
        lease_expires_at=_future(),
    )
    assert response.status_code == 200
    assert response.headers["X-IPAM-Ignored-Aspects"] == "assignment"
    host = response.get_json()
    assert host["assignment_type"] == persistent
    assert host["assignment_source"] is None
    # The lease aspect is still applied.
    assert host["lease_active"] is True


def test_persistent_assignment_can_switch_or_be_cleared_explicitly(
    client, network
):
    _upsert(client, ip_address="10.9.0.14", assignment_type="reservation")
    switched = _upsert(client, ip_address="10.9.0.14", assignment_type="static")
    assert switched.get_json()["assignment_type"] == "static"

    cleared = _upsert(client, ip_address="10.9.0.14", assignment_type=None)
    assert cleared.status_code == 200
    assert cleared.get_json()["assignment_type"] is None


def test_expired_dynamic_lease_does_not_release_persistent_assignment(
    client, network
):
    _upsert(client, ip_address="10.9.0.15", assignment_type="static")
    _upsert(client, ip_address="10.9.0.15", lease_expires_at=_past())
    available = client.get(
        f"/api/v1/ip/networks/{network['id']}/available-ips", headers=AUTH
    ).get_json()
    assert "10.9.0.15" not in available["available_ips"]


# --- Partial updates and independence ---------------------------------


def test_reservation_import_preserves_metadata_lease_and_health(
    client, network
):
    _upsert(
        client,
        ip_address="10.9.0.20",
        hostname="nas",
        cname="files",
        description="curated by hand",
        lease_expires_at=_future(),
        lease_source="udm-leases",
        last_seen=_past(0.1),
        last_seen_source="ping",
        status="active",
    )
    for _ in range(2):  # repeated identical imports
        response = _upsert(
            client,
            ip_address="10.9.0.20",
            mac_address="aa:bb:cc:00:00:20",
            assignment_type="reservation",
            assignment_source="udm-reservations",
            discovery_source="udm-reservations",
        )
        assert response.status_code == 200

    host = response.get_json()
    assert host["hostname"] == "nas"
    assert host["cname"] == "files"
    assert host["description"] == "curated by hand"
    assert host["status"] == "active"
    assert host["lease_source"] == "udm-leases"
    assert host["lease_active"] is True
    assert host["last_seen_source"] == "ping"
    assert host["last_seen"] is not None
    assert Host.query.filter_by(ip_address="10.9.0.20").count() == 1


def test_clearing_one_aspect_keeps_the_others(client, network):
    _upsert(
        client,
        ip_address="10.9.0.21",
        assignment_type="reservation",
        lease_expires_at=_future(),
        lease_source="udm-leases",
        last_seen=_past(),
        last_seen_source="ping",
    )
    response = _upsert(
        client,
        ip_address="10.9.0.21",
        lease_expires_at=None,
        lease_source=None,
    )
    host = response.get_json()
    assert host["lease_expires_at"] is None
    assert host["assignment_type"] == "reservation"
    assert host["last_seen_source"] == "ping"

    response = _upsert(client, ip_address="10.9.0.21", last_seen=None)
    host = response.get_json()
    assert host["last_seen"] is None
    assert host["assignment_type"] == "reservation"


def test_put_without_new_fields_keeps_them(client, network):
    created = _upsert(
        client,
        ip_address="10.9.0.22",
        assignment_type="static",
        lease_expires_at=_future(),
    ).get_json()

    response = client.put(
        f"/api/v1/hosts/{created['id']}",
        json={"ip_address": "10.9.0.22", "hostname": "legacy-client"},
        headers=AUTH,
    )
    assert response.status_code == 200
    host = response.get_json()
    assert host["hostname"] == "legacy-client"
    assert host["assignment_type"] == "static"
    assert host["lease_expires_at"] is not None


# --- Timestamps --------------------------------------------------------


def test_older_observation_does_not_replace_newer(client, network):
    newer = _past(1)
    _upsert(
        client, ip_address="10.9.0.30", last_seen=newer, last_seen_source="a"
    )
    response = _upsert(
        client,
        ip_address="10.9.0.30",
        last_seen=_past(5),
        last_seen_source="b",
    )
    assert response.headers["X-IPAM-Ignored-Aspects"] == "observation"
    host = response.get_json()
    assert host["last_seen_source"] == "a"
    assert host["last_seen"].startswith(newer[:19])


def test_older_lease_and_assignment_confirmations_are_ignored(client, network):
    _upsert(
        client,
        ip_address="10.9.0.31",
        assignment_type="reservation",
        assignment_source="new",
        assignment_last_confirmed_at=_past(1),
        lease_expires_at=_future(5),
        lease_observed_at=_past(1),
    )
    response = _upsert(
        client,
        ip_address="10.9.0.31",
        assignment_type="static",
        assignment_source="old",
        assignment_last_confirmed_at=_past(10),
        lease_expires_at=_past(3),
        lease_observed_at=_past(10),
    )
    assert response.headers["X-IPAM-Ignored-Aspects"] == "assignment,lease"
    host = response.get_json()
    assert host["assignment_source"] == "new"
    assert host["assignment_type"] == "reservation"
    assert host["lease_active"] is True


def test_timestamps_are_utc_aware(client, network):
    response = _upsert(
        client,
        ip_address="10.9.0.32",
        lease_expires_at="2030-01-01T12:00:00+02:00",
    )
    assert response.get_json()["lease_expires_at"] == (
        "2030-01-01T10:00:00+00:00"
    )


def test_naive_timestamp_rejected_for_new_fields(client, network):
    response = _upsert(
        client, ip_address="10.9.0.33", lease_expires_at="2030-01-01T12:00:00"
    )
    assert response.status_code == 400
    assert Host.query.filter_by(ip_address="10.9.0.33").first() is None


def test_naive_last_seen_still_accepted_as_utc(client, network):
    response = _upsert(
        client, ip_address="10.9.0.34", last_seen="2030-01-01T12:00:00"
    )
    assert response.status_code == 201
    assert response.get_json()["last_seen"] == "2030-01-01T12:00:00+00:00"


@pytest.mark.parametrize(
    "body",
    [
        {"assignment_type": "pool"},
        {"assignment_type": 3},
        {"lease_expires_at": "tomorrow"},
        {"assignment_last_confirmed_at": 12},
        {"lease_source": "x" * 51},
    ],
)
def test_invalid_values_rejected_without_changes(client, network, body):
    _upsert(client, ip_address="10.9.0.35", assignment_type="static")
    response = _upsert(client, ip_address="10.9.0.35", **body)
    assert response.status_code == 400
    assert Host.query.filter_by(
        ip_address="10.9.0.35"
    ).one().assignment_type == ("static")


def test_parse_timestamp_converts_to_naive_utc():
    assert parse_timestamp("2026-10-31T21:00:00+01:00") == datetime(
        2026, 10, 31, 20, 0
    )
    assert parse_timestamp("2026-10-31T20:00:00Z") == datetime(
        2026, 10, 31, 20, 0
    )


# --- MAC conflicts -----------------------------------------------------


def test_mac_mismatch_on_reservation_is_a_visible_conflict(client, network):
    _upsert(
        client,
        ip_address="10.9.0.40",
        mac_address="AA:BB:CC:00:00:40",
        assignment_type="reservation",
        last_seen=_past(),
    )
    response = _upsert(
        client, ip_address="10.9.0.40", mac_address="aa:bb:cc:99:99:99"
    )
    assert response.status_code == 409
    body = response.get_json()
    assert body["existing_mac_address"] == "AA:BB:CC:00:00:40"
    host = Host.query.filter_by(ip_address="10.9.0.40").one()
    assert host.mac_address == "AA:BB:CC:00:00:40"


def test_same_mac_in_other_notation_is_not_a_conflict(client, network):
    _upsert(
        client,
        ip_address="10.9.0.41",
        mac_address="AA:BB:CC:00:00:41",
        assignment_type="reservation",
    )
    response = _upsert(
        client, ip_address="10.9.0.41", mac_address="aa-bb-cc-00-00-41"
    )
    assert response.status_code == 200


def test_confirmed_mac_change_drops_old_device_history(client, network):
    _upsert(
        client,
        ip_address="10.9.0.42",
        mac_address="aa:bb:cc:00:00:42",
        assignment_type="reservation",
        lease_expires_at=_future(),
        last_seen=_past(),
        description="kept",
    )
    response = _upsert(
        client,
        ip_address="10.9.0.42",
        mac_address="aa:bb:cc:00:00:43",
        confirm_mac_change=True,
    )
    assert response.status_code == 200
    host = response.get_json()
    assert host["mac_address"] == "aa:bb:cc:00:00:43"
    assert host["assignment_type"] == "reservation"
    assert host["lease_expires_at"] is None
    assert host["last_seen"] is None
    assert host["description"] == "kept"


def test_mac_change_without_persistent_assignment_is_allowed(client, network):
    _upsert(client, ip_address="10.9.0.43", mac_address="aa:bb:cc:00:00:01")
    response = _upsert(
        client, ip_address="10.9.0.43", mac_address="aa:bb:cc:00:00:02"
    )
    assert response.status_code == 200


# --- Availability ------------------------------------------------------


def test_availability_is_consistent_across_endpoints(client, app, network):
    net = db.session.get(Network, network["id"])
    db.session.add(
        DhcpRange(
            network_id=net.id,
            start_ip="10.9.0.100",
            end_ip="10.9.0.199",
            is_active=True,
        )
    )
    db.session.commit()
    _upsert(client, ip_address="10.9.0.1", assignment_type="static")
    # Expired lease inside the pool, observation-only host outside it.
    _upsert(client, ip_address="10.9.0.150", lease_expires_at=_past())
    _upsert(client, ip_address="10.9.0.2", last_seen=_past())

    available = client.get(
        f"/api/v1/ip/networks/{net.id}/available-ips", headers=AUTH
    ).get_json()
    next_ip = client.get(
        f"/api/v1/ip/networks/{net.id}/next-ip", headers=AUTH
    ).get_json()

    assert next_ip["ip_address"] == "10.9.0.3"
    assert available["available_ips"][0] == "10.9.0.3"
    assert "10.9.0.150" not in available["available_ips"]
    pool = {f"10.9.0.{i}" for i in range(100, 200)}
    assert not pool & set(available["available_ips"])
    db.session.refresh(net)
    assert net.available_hosts == available["total_available"]
    # 254 hosts - 100 pool - 2 recorded outside the pool.
    assert available["total_available"] == 152


def test_ip_query_distinguishes_no_record_from_confirmed_free(client, network):
    response = client.get("/api/v1/ip/10.9.0.77", headers=AUTH)
    body = response.get_json()
    assert body["status"] == "available"
    assert body["allocation_state"] == "no_record"
    assert body["confirmed_free"] is False

    _upsert(client, ip_address="10.9.0.78", assignment_type="reservation")
    body = client.get("/api/v1/ip/10.9.0.78", headers=AUTH).get_json()
    assert body["status"] == "assigned"
    assert body["allocation_state"] == "reserved"
    assert body["host"]["assignment_type"] == "reservation"


# --- Legacy behaviour and listing --------------------------------------


def test_legacy_flags_do_not_imply_assignment_type(client, network):
    response = _upsert(
        client, ip_address="10.9.0.50", is_assigned=True, status="active"
    )
    host = response.get_json()
    assert host["assignment_type"] is None
    assert host["allocation_state"] == "unknown"


def test_list_filter_by_assignment_type(client, network):
    _upsert(client, ip_address="10.9.0.60", assignment_type="reservation")
    _upsert(client, ip_address="10.9.0.61", assignment_type="static")
    _upsert(client, ip_address="10.9.0.62")

    def ips(query):
        response = client.get(f"/api/v1/hosts?{query}", headers=AUTH)
        assert response.status_code == 200
        return {h["ip_address"] for h in response.get_json()["data"]}

    assert ips("assignment_type=reservation") == {"10.9.0.60"}
    assert ips("assignment_type=unset") == {"10.9.0.62"}
    response = client.get("/api/v1/hosts?assignment_type=bogus", headers=AUTH)
    assert response.status_code == 400


def test_create_endpoint_accepts_assignment_fields(client, network):
    response = client.post(
        "/api/v1/hosts",
        json={
            "ip_address": "10.9.0.70",
            "assignment_type": "static",
            "assignment_source": "manual",
        },
        headers=AUTH,
    )
    assert response.status_code == 201
    assert response.get_json()["allocation_state"] == "static"


# --- Web UI and import/export -------------------------------------------


def test_web_edit_sets_manual_assignment(client, network):
    host = _upsert(client, ip_address="10.9.0.80").get_json()
    response = client.post(
        f"/edit_host/{host['id']}",
        data={
            "ip_address": "10.9.0.80",
            "status": "active",
            "assignment_type": "static",
            "network_id": 0,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    stored = db.session.get(Host, host["id"])
    assert stored.assignment_type == "static"
    assert stored.assignment_source == "manual"
    assert stored.assignment_last_confirmed_at is not None

    page = client.get("/hosts")
    assert b"Statically allocated" in page.data


def test_json_export_import_roundtrip(client, network):
    _upsert(
        client,
        ip_address="10.9.0.90",
        assignment_type="reservation",
        assignment_source="udm-reservations",
        lease_expires_at="2030-01-01T00:00:00Z",
        lease_source="udm-leases",
    )
    exported = client.get("/export/hosts/json").data
    entry = next(
        e
        for e in json.loads(exported)["data"]
        if e["ip_address"] == "10.9.0.90"
    )
    assert entry["assignment_type"] == "reservation"
    assert entry["lease_expires_at"] == "2030-01-01T00:00:00+00:00"

    from importers.json_importer import JSONImporter

    importer = JSONImporter()
    raw = importer.import_hosts(exported)
    valid, errors = importer.validate_hosts_data(raw)
    assert not errors
    imported = next(h for h in valid if h["ip_address"] == "10.9.0.90")
    assert imported["assignment_type"] == "reservation"
    assert imported["lease_expires_at"] == datetime(2030, 1, 1)


def test_csv_export_contains_assignment_columns(client, network):
    _upsert(client, ip_address="10.9.0.91", assignment_type="static")
    csv_text = client.get("/export/hosts/csv").data.decode()
    header = csv_text.splitlines()[0]
    assert header.endswith("Last Seen Source")
    assert "Assignment Type" in header

    from importers.csv_importer import CSVImporter

    importer = CSVImporter()
    valid, errors = importer.validate_hosts_data(
        importer.import_hosts(csv_text.encode())
    )
    assert not errors
    assert valid[0]["assignment_type"] == "static"


def test_invalid_assignment_type_in_import_is_reported():
    from importers.json_importer import JSONImporter

    importer = JSONImporter()
    valid, errors = importer.validate_hosts_data(
        [{"ip_address": "10.9.0.92", "assignment_type": "bogus"}]
    )
    assert not valid
    assert "assignment_type" in errors[0]


# --- Migration ---------------------------------------------------------


def test_migration_preserves_data_and_backfills_reservations():
    """Upgrade a populated pre-migration database and downgrade again."""
    from flask_migrate import downgrade, upgrade

    from ipam import create_app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        app = create_app(
            "default", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}"}
        )
        with app.app_context():
            upgrade(revision="c3f2a4b7d9e1")
            db.engine.dispose()

        con = sqlite3.connect(path)
        con.executemany(
            "INSERT INTO hosts (ip_address, hostname, status, is_assigned, "
            "discovery_source, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("10.1.0.1", "res", "reserved", 1, "udm-reservations", None),
                ("10.1.0.2", "act", "active", 1, None, "2026-01-01 00:00:00"),
                ("10.1.0.3", "other", "reserved", 1, "manual", None),
                ("10.1.0.4", "unas", "reserved", 0, "udm-reservations", None),
            ],
        )
        con.commit()
        con.close()

        with app.app_context():
            upgrade()
            db.engine.dispose()

        con = sqlite3.connect(path)
        rows = dict(
            (r[0], r[1:])
            for r in con.execute(
                "SELECT ip_address, hostname, assignment_type, "
                "assignment_source, assignment_last_confirmed_at, last_seen "
                "FROM hosts"
            )
        )
        con.close()
        assert rows["10.1.0.1"] == (
            "res",
            "reservation",
            "udm-reservations",
            None,
            None,
        )
        # Never inferred from is_assigned/status alone.
        assert rows["10.1.0.2"][1:4] == (None, None, None)
        assert rows["10.1.0.2"][4] is not None
        assert rows["10.1.0.3"][1] is None
        assert rows["10.1.0.4"][1] is None

        with app.app_context():
            downgrade(revision="c3f2a4b7d9e1")
            db.engine.dispose()
        con = sqlite3.connect(path)
        columns = {r[1] for r in con.execute("PRAGMA table_info(hosts)")}
        count = con.execute("SELECT COUNT(*) FROM hosts").fetchone()[0]
        con.close()
        assert "assignment_type" not in columns
        assert count == 4
    finally:
        os.unlink(path)


def test_available_ips_limit_query_parameter(client, network):
    response = client.get(
        f"/api/v1/ip/networks/{network['id']}/available-ips?limit=3",
        headers=AUTH,
    )
    assert response.status_code == 200
    assert response.get_json()["available_ips"] == [
        "10.9.0.1",
        "10.9.0.2",
        "10.9.0.3",
    ]
