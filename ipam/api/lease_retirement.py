"""Atomic, source-scoped retirement of expired dynamic host records."""

import re
from datetime import UTC, datetime, timedelta

from flask import current_app, request
from flask_restx import abort
from sqlalchemy import Boolean, DateTime, Integer, String, delete

from ipam.allocation import parse_timestamp
from ipam.extensions import db
from ipam.models import Host


def expected_snapshot(data, host_id):
    """Parse the complete host snapshot a guarded request is based on."""
    expected = data.get("expected")
    if not isinstance(expected, dict):
        raise ValueError("expected must contain the previously read host")
    values = {}
    for column in Host.__table__.columns:
        field = column.name
        if field not in expected:
            raise ValueError(f"expected.{field} is required")
        value = expected[field]
        if value is None:
            if not column.nullable:
                raise ValueError(f"expected.{field} cannot be null")
        elif isinstance(column.type, DateTime):
            value = parse_timestamp(value, require_timezone=True)
        elif isinstance(column.type, Boolean):
            if not isinstance(value, bool):
                raise ValueError(f"expected.{field} must be a boolean")
        elif isinstance(column.type, Integer):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"expected.{field} must be an integer")
        elif isinstance(column.type, String) and not isinstance(value, str):
            raise ValueError(f"expected.{field} must be a string or null")
        values[field] = value
    if values["id"] != host_id:
        raise ValueError("expected.id must match the URL")
    return values


def retire_lease(host_id):
    """Delete only a matching, uncurated, expired dynamic snapshot.

    The collector supplies a complete successful source snapshot and grace
    cutoff. All stored columns participate in the DELETE predicate, preventing
    a renewal, reassignment or manual edit between preview and execution from
    deleting a different version of the record. No read-then-delete window.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "A JSON object is required")
    try:
        source = data.get("source")
        if (
            not isinstance(source, str)
            or not source.strip()
            or len(source) > 50
        ):
            raise ValueError("source must be a nonempty string (max 50 chars)")
        cutoff = parse_timestamp(
            data.get("expired_before"), require_timezone=True
        )
        if cutoff is None:
            raise ValueError("expired_before is required")
        expected = expected_snapshot(data, host_id)
    except (TypeError, ValueError) as error:
        abort(400, str(error))

    now = datetime.now(UTC).replace(tzinfo=None)
    if cutoff > now:
        abort(400, "expired_before must not be in the future")
    minimum_age = current_app.config["LEASE_RETIRE_MIN_AGE_SECONDS"]
    cutoff = min(cutoff, now - timedelta(seconds=minimum_age))
    if (
        expected["assignment_type"] != "dynamic"
        or any(
            expected[field] != source
            for field in (
                "assignment_source",
                "lease_source",
                "discovery_source",
            )
        )
        or any(
            expected[field]
            for field in (
                "is_assigned",
                "cname",
                "description",
                "last_seen",
                "last_seen_source",
            )
        )
        or not re.fullmatch(
            r"[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}", expected["mac_address"] or ""
        )
        or any(
            expected[field] is None or expected[field] > now
            for field in ("assignment_last_confirmed_at", "lease_observed_at")
        )
        or expected["lease_expires_at"] is None
        or expected["lease_expires_at"] > cutoff
    ):
        abort(
            409,
            "Host is protected, not source-owned, or lease grace period has not elapsed",
        )

    result = db.session.execute(
        delete(Host)
        .where(*snapshot_conditions(expected))
        .execution_options(synchronize_session=False)
    )
    abort_unless_single_row(result, host_id)
    db.session.commit()
    return "", 204


def snapshot_conditions(expected):
    """Return WHERE conditions matching every stored column of a snapshot."""
    conditions = []
    for field, value in expected.items():
        column = getattr(Host, field)
        conditions.append(
            column.is_(None) if value is None else column == value
        )
    return conditions


def abort_unless_single_row(result, host_id):
    """Roll back and abort with 404/412 unless exactly one row matched."""
    if result.rowcount == 1:
        return
    db.session.rollback()
    if db.session.get(Host, host_id) is None:
        abort(404, "Host not found")
    abort(
        412,
        "Host changed since the supplied snapshot; read and reconcile again",
    )
