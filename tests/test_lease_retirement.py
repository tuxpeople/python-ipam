"""Guarded retirement must not delete renewed, curated or reassigned hosts."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import DateTime, update

from ipam.allocation import parse_timestamp
from ipam.extensions import db
from ipam.models import Host

AUTH = {"Authorization": "Bearer test-token"}
SOURCE = "udm-leases"


def iso(hours):
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


@pytest.fixture
def snapshot(client):
    response = client.post(
        "/api/v1/hosts/upsert",
        headers=AUTH,
        json={
            "ip_address": "10.9.0.223",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "old-device",
            "is_assigned": False,
            "assignment_type": "dynamic",
            "assignment_source": SOURCE,
            "assignment_last_confirmed_at": iso(-4),
            "lease_expires_at": iso(-2),
            "lease_source": SOURCE,
            "lease_observed_at": iso(-4),
            "discovery_source": SOURCE,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def retire(client, snapshot, **overrides):
    return client.post(
        f"/api/v1/hosts/{snapshot['id']}/retire-lease",
        headers=AUTH,
        json={
            "source": SOURCE,
            "expired_before": iso(0),
            "expected": snapshot,
            **overrides,
        },
    )


def stored(client, snapshot):
    return client.get(f"/api/v1/hosts/{snapshot['id']}", headers=AUTH)


def edit_host(client, snapshot, field, value):
    """Model a persisted edit without depending on legacy PUT null validation."""
    if value is not None and isinstance(
        Host.__table__.columns[field].type, DateTime
    ):
        value = parse_timestamp(value, require_timezone=True)
    db.session.execute(
        update(Host).where(Host.id == snapshot["id"]).values({field: value})
    )
    db.session.commit()
    return stored(client, snapshot)


def test_delete_matching_expired_dynamic_snapshot(client, snapshot):
    assert retire(client, snapshot).status_code == 204
    assert stored(client, snapshot).status_code == 404
    assert retire(client, snapshot).status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("assignment_type", "reservation"),
        ("assignment_type", "static"),
        ("assignment_source", "manual"),
        ("lease_source", "other-dhcp"),
        ("discovery_source", "nmap"),
        ("is_assigned", True),
        ("cname", "service"),
        ("description", "Keep this host"),
        ("last_seen", "2026-01-01T00:00:00+00:00"),
        ("last_seen_source", "nmap"),
        ("mac_address", None),
        ("assignment_last_confirmed_at", None),
        ("lease_observed_at", None),
        ("lease_expires_at", None),
    ],
)
def test_protected_current_snapshot_rejected(client, snapshot, field, value):
    response = edit_host(client, snapshot, field, value)
    assert response.status_code == 200
    assert retire(client, response.get_json()).status_code == 409
    assert stored(client, snapshot).status_code == 200


@pytest.mark.parametrize(
    "field,value",
    [
        ("hostname", "renamed"),
        ("mac_address", "00:11:22:33:44:55"),
        ("status", "inactive"),
        ("description", "edited during sync"),
        ("assignment_type", "reservation"),
        ("assignment_last_confirmed_at", "2026-01-01T00:00:00+00:00"),
        ("lease_observed_at", "2026-01-01T00:00:00+00:00"),
        ("last_seen", "2026-01-01T00:00:00+00:00"),
    ],
)
def test_stale_snapshot_cannot_delete_changed_record(
    client, snapshot, field, value
):
    response = edit_host(client, snapshot, field, value)
    assert response.status_code == 200
    assert retire(client, snapshot).status_code == 412
    assert (
        stored(client, snapshot).get_json()[field] == response.get_json()[field]
    )


def test_renewed_lease_cannot_be_deleted_with_old_snapshot(client, snapshot):
    response = client.post(
        "/api/v1/hosts/upsert",
        headers=AUTH,
        json={
            "ip_address": snapshot["ip_address"],
            "lease_expires_at": iso(1),
            "lease_observed_at": iso(0),
        },
    )
    assert response.status_code == 200
    assert retire(client, snapshot).status_code == 412
    assert retire(client, response.get_json()).status_code == 409
    assert stored(client, snapshot).status_code == 200


def test_atomic_delete_checks_change_after_validation(
    client, snapshot, monkeypatch
):
    execute = db.session.execute
    raced = []

    def concurrent_edit(statement, *args, **kwargs):
        if getattr(statement, "is_delete", False) and not raced:
            raced.append(True)
            execute(
                update(Host)
                .where(Host.id == snapshot["id"])
                .values(description="concurrent edit")
            )
            db.session.commit()
        return execute(statement, *args, **kwargs)

    monkeypatch.setattr(db.session, "execute", concurrent_edit)
    assert retire(client, snapshot).status_code == 412
    assert raced
    assert (
        stored(client, snapshot).get_json()["description"] == "concurrent edit"
    )


def test_server_enforces_minimum_age_even_with_recent_cutoff(
    client, snapshot, app
):
    app.config["LEASE_RETIRE_MIN_AGE_SECONDS"] = 3 * 3600
    assert retire(client, snapshot).status_code == 409
    app.config["LEASE_RETIRE_MIN_AGE_SECONDS"] = 3600
    assert retire(client, snapshot).status_code == 204


def test_client_can_request_longer_grace(client, snapshot):
    assert retire(client, snapshot, expired_before=iso(-3)).status_code == 409
    assert stored(client, snapshot).status_code == 200


@pytest.mark.parametrize("cutoff", [None, "bad", "2026-01-01T00:00:00", 0])
def test_bad_cutoff_rejected(client, snapshot, cutoff):
    assert retire(client, snapshot, expired_before=cutoff).status_code == 400
    assert stored(client, snapshot).status_code == 200


def test_future_cutoff_rejected(client, snapshot):
    assert retire(client, snapshot, expired_before=iso(1)).status_code == 400


@pytest.mark.parametrize("field", list(Host.__table__.columns.keys()))
def test_incomplete_snapshot_rejected(client, snapshot, field):
    expected = {k: v for k, v in snapshot.items() if k != field}
    assert retire(client, snapshot, expected=expected).status_code == 400
    assert stored(client, snapshot).status_code == 200


@pytest.mark.parametrize("source", [None, "", "other-source", 12])
def test_wrong_or_invalid_source_rejected(client, snapshot, source):
    assert retire(client, snapshot, source=source).status_code in (400, 409)
    assert stored(client, snapshot).status_code == 200


def test_normal_authentication_required(client, snapshot):
    response = client.post(
        f"/api/v1/hosts/{snapshot['id']}/retire-lease",
        json={"source": SOURCE, "expired_before": iso(0), "expected": snapshot},
    )
    assert response.status_code == 401
    assert stored(client, snapshot).status_code == 200


@pytest.mark.parametrize("expected", [None, [], {"id": "1"}])
def test_invalid_snapshot_rejected(client, snapshot, expected):
    assert retire(client, snapshot, expected=expected).status_code == 400


def test_invalid_body_rejected(client, snapshot):
    response = client.post(
        f"/api/v1/hosts/{snapshot['id']}/retire-lease",
        headers=AUTH,
        json=[],
    )
    assert response.status_code == 400
