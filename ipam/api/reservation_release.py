"""Atomic, snapshot-checked release of reservations removed at the source."""

import re
from datetime import UTC, datetime

from flask import request
from flask_restx import abort
from sqlalchemy import delete, update

from ipam.allocation import (
    ASSIGNMENT_DYNAMIC,
    ASSIGNMENT_RESERVATION,
    normalize_mac,
    parse_source,
    parse_timestamp,
)
from ipam.api.lease_retirement import (
    abort_unless_single_row,
    expected_snapshot,
    snapshot_conditions,
)
from ipam.extensions import db
from ipam.models import Host, Network
from ipam.normalize import strip_domain_suffix

ACTION_DELETE = "delete"
ACTION_CONVERT = "convert"

_MAC_PATTERN = re.compile(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}")


def _parse_lease(data, now):
    """Validate the current lease a reservation is converted to."""
    lease = data.get("lease")
    if not isinstance(lease, dict):
        raise ValueError("lease is required for action=convert")
    mac = normalize_mac(lease.get("mac_address"))
    if not mac or not _MAC_PATTERN.fullmatch(mac):
        raise ValueError("lease.mac_address must be a valid MAC address")
    lease_source = parse_source(lease.get("lease_source"), "lease.lease_source")
    if lease_source is None:
        raise ValueError("lease.lease_source is required")
    expires = parse_timestamp(
        lease.get("lease_expires_at"), require_timezone=True
    )
    observed = parse_timestamp(
        lease.get("lease_observed_at"), require_timezone=True
    )
    if expires is None or observed is None:
        raise ValueError(
            "lease.lease_expires_at and lease.lease_observed_at are required"
        )
    if observed > now:
        raise ValueError("lease.lease_observed_at must not be in the future")
    hostname = lease.get("hostname")
    if hostname is not None and not isinstance(hostname, str):
        raise ValueError("lease.hostname must be a string or null")
    return {
        "mac_address": mac,
        "lease_source": lease_source,
        "lease_expires_at": expires,
        "lease_observed_at": observed,
        "has_hostname": "hostname" in lease,
        "hostname": hostname.strip() or None if hostname else None,
    }


def release_reservation(host_id):
    """Delete or convert a reservation that disappeared from its source.

    The caller supplies the complete previously read host. Both actions
    apply only if every stored column still matches, in one atomic
    statement, so a renewal, MAC change or manual edit after the read
    cannot be overwritten or deleted.

    - ``delete`` removes the host, but never while the stored lease is
      still valid: removing a reservation must not free an address that
      a current lease still claims.
    - ``convert`` turns the reservation into a dynamic allocation backed
      by the supplied current lease. A different MAC means a different
      device; its hostname and device observation are then replaced.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "A JSON object is required")
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        source = parse_source(data.get("source"), "source")
        if source is None:
            raise ValueError("source must be a nonempty string (max 50 chars)")
        action = data.get("action")
        if action not in (ACTION_DELETE, ACTION_CONVERT):
            raise ValueError("action must be 'delete' or 'convert'")
        expected = expected_snapshot(data, host_id)
        lease = _parse_lease(data, now) if action == ACTION_CONVERT else None
    except (TypeError, ValueError) as error:
        abort(400, str(error))

    if (
        expected["assignment_type"] != ASSIGNMENT_RESERVATION
        or expected["assignment_source"] != source
    ):
        abort(409, "Host is not a reservation owned by this source")

    if action == ACTION_DELETE:
        if (
            expected["lease_expires_at"] is not None
            and expected["lease_expires_at"] > now
        ):
            abort(
                409,
                "Stored lease is still valid; convert instead of deleting",
            )
        result = db.session.execute(
            delete(Host)
            .where(*snapshot_conditions(expected))
            .execution_options(synchronize_session=False)
        )
        abort_unless_single_row(result, host_id)
        db.session.commit()
        return None

    if lease["lease_expires_at"] <= now:
        abort(409, "Lease has expired; delete instead of converting")
    if (
        expected["lease_observed_at"] is not None
        and lease["lease_observed_at"] < expected["lease_observed_at"]
    ):
        abort(409, "Lease observation is older than the stored one")

    values = {
        "assignment_type": ASSIGNMENT_DYNAMIC,
        "assignment_source": lease["lease_source"],
        "assignment_last_confirmed_at": lease["lease_observed_at"],
        "is_assigned": False,
        "discovery_source": lease["lease_source"],
        "mac_address": lease["mac_address"],
        "lease_source": lease["lease_source"],
        "lease_expires_at": lease["lease_expires_at"],
        "lease_observed_at": lease["lease_observed_at"],
    }
    network = (
        db.session.get(Network, expected["network_id"])
        if expected["network_id"]
        else None
    )
    hostname = strip_domain_suffix(
        lease["hostname"], network.domain if network else None
    )
    if lease["mac_address"] != normalize_mac(expected["mac_address"]):
        # Another device now holds the address.
        values.update(hostname=hostname, last_seen=None, last_seen_source=None)
    elif lease["has_hostname"]:
        values["hostname"] = hostname

    result = db.session.execute(
        update(Host)
        .where(*snapshot_conditions(expected))
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    abort_unless_single_row(result, host_id)
    db.session.commit()
    db.session.expire_all()
    return db.session.get(Host, host_id)
