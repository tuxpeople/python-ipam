"""Address assignment, lease and observation semantics.

A host record carries three independent aspects (see
``ADDRESS_ASSIGNMENT_MODEL.md``):

* **assignment** -- how the address is allocated
  (``assignment_type``: reservation, static, dynamic, unknown), with
  ``assignment_source`` and ``assignment_last_confirmed_at``.
* **lease** -- an explicitly observed DHCP lease
  (``lease_expires_at``), with ``lease_source`` and
  ``lease_observed_at``.
* **observation** -- the latest actual sighting of the device
  (``last_seen``), with ``last_seen_source``.

The combined allocation state is derived from these facts and never
persisted, so contradictory status values cannot accumulate.

All timestamps are stored as naive UTC in the database and exposed as
timezone-aware UTC through the API.
"""

from datetime import UTC, datetime

ASSIGNMENT_RESERVATION = "reservation"
ASSIGNMENT_STATIC = "static"
ASSIGNMENT_DYNAMIC = "dynamic"
ASSIGNMENT_UNKNOWN = "unknown"

ASSIGNMENT_TYPES = (
    ASSIGNMENT_RESERVATION,
    ASSIGNMENT_STATIC,
    ASSIGNMENT_DYNAMIC,
    ASSIGNMENT_UNKNOWN,
)

#: Assignment types that represent a deliberate, persistent allocation.
#: These are never replaced by a lease or by missed observations.
PERSISTENT_ASSIGNMENT_TYPES = frozenset(
    {ASSIGNMENT_RESERVATION, ASSIGNMENT_STATIC}
)

#: Fields that make up each independent aspect, keyed by aspect name.
ASPECT_FIELDS = {
    "assignment": (
        "assignment_type",
        "assignment_source",
        "assignment_last_confirmed_at",
    ),
    "lease": ("lease_expires_at", "lease_source", "lease_observed_at"),
    "observation": ("last_seen", "last_seen_source"),
}

#: The timestamp that orders updates of each aspect.
ASPECT_FRESHNESS_FIELD = {
    "assignment": "assignment_last_confirmed_at",
    "lease": "lease_observed_at",
    "observation": "last_seen",
}

TIMESTAMP_FIELDS = frozenset(
    {
        "assignment_last_confirmed_at",
        "lease_expires_at",
        "lease_observed_at",
        "last_seen",
    }
)

# Derived allocation states (machine name -> human readable label).
STATE_RESERVED = "reserved"
STATE_RESERVED_LEASE_ACTIVE = "reserved_lease_active"
STATE_STATIC = "static"
STATE_DYNAMIC = "dynamic"
STATE_LEASE_EXPIRED = "lease_expired"
STATE_OBSERVED = "observed"
STATE_UNKNOWN = "unknown"
STATE_NO_RECORD = "no_record"

ALLOCATION_STATE_LABELS = {
    STATE_RESERVED: "Reserved",
    STATE_RESERVED_LEASE_ACTIVE: "Reserved; lease active",
    STATE_STATIC: "Statically allocated",
    STATE_DYNAMIC: "Dynamically allocated",
    STATE_LEASE_EXPIRED: "No confirmed current allocation",
    STATE_OBSERVED: "Observed; assignment unknown",
    STATE_UNKNOWN: "Recorded; assignment unknown",
    STATE_NO_RECORD: "No recorded allocation",
}


def utcnow():
    """Return the current time as naive UTC (database representation)."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_db_utc(value):
    """Convert a datetime to naive UTC for storage.

    Timezone-aware values are converted to UTC; naive values are
    assumed to already be UTC.
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


def to_api_utc(value):
    """Return a stored (naive UTC) datetime as timezone-aware UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_timestamp(value, require_timezone=True):
    """Parse an ISO 8601 timestamp into naive UTC.

    Args:
        value: ``None``, a ``datetime`` or an ISO 8601 string. A
            trailing ``Z`` is accepted as UTC.
        require_timezone: Reject timestamps without an explicit UTC
            offset. Legacy fields (``last_seen``) pass ``False`` and
            treat naive input as UTC.

    Raises:
        ValueError: The value is not a valid timestamp.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith(("Z", "z")):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {value!r}") from e
    else:
        raise ValueError("Expected an ISO 8601 timestamp")
    if require_timezone and parsed.tzinfo is None:
        raise ValueError(
            f"Timestamp {value!r} must include a timezone offset "
            "(e.g. 'Z' or '+00:00')"
        )
    return to_db_utc(parsed)


def parse_assignment_type(value):
    """Validate an assignment type; ``None`` clears it."""
    if value is None:
        return None
    if not isinstance(value, str) or value not in ASSIGNMENT_TYPES:
        allowed = ", ".join(ASSIGNMENT_TYPES)
        raise ValueError(
            f"Invalid assignment_type {value!r}; expected one of: {allowed}"
        )
    return value


def parse_source(value, field):
    """Validate a provenance source identifier."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if len(value) > 50:
        raise ValueError(f"{field} must be at most 50 characters")
    return value or None


def parse_aspect_field(field, value):
    """Validate and normalize one assignment/lease/observation field."""
    if field == "assignment_type":
        return parse_assignment_type(value)
    if field == "last_seen":
        # Legacy field: naive timestamps are accepted and treated as UTC.
        return parse_timestamp(value, require_timezone=False)
    if field in TIMESTAMP_FIELDS:
        return parse_timestamp(value)
    return parse_source(value, field)


def normalize_mac(value):
    """Return a canonical lowercase colon-separated MAC, or ``None``."""
    if not value:
        return None
    digits = "".join(c for c in str(value).lower() if c in "0123456789abcdef")
    if len(digits) != 12:
        return str(value).strip().lower()
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


def lease_is_active(host, now=None):
    """Return True if the host has an explicitly observed, unexpired lease."""
    if host.lease_expires_at is None:
        return False
    now = now or utcnow()
    return to_db_utc(host.lease_expires_at) > now


def has_persistent_assignment(host):
    """Return True for reservation or static assignments."""
    return host.assignment_type in PERSISTENT_ASSIGNMENT_TYPES


def derive_allocation_state(host, now=None):
    """Derive the allocation display state from the recorded facts.

    The state is never persisted. Note that every derived state of an
    existing record keeps the address out of allocation suggestions: an
    expired lease or a missed observation is not proof that an address
    is free.
    """
    if host is None:
        return STATE_NO_RECORD
    active = lease_is_active(host, now)
    if host.assignment_type == ASSIGNMENT_RESERVATION:
        return STATE_RESERVED_LEASE_ACTIVE if active else STATE_RESERVED
    if host.assignment_type == ASSIGNMENT_STATIC:
        return STATE_STATIC
    if active:
        return STATE_DYNAMIC
    if host.lease_expires_at is not None:
        return STATE_LEASE_EXPIRED
    if host.assignment_type == ASSIGNMENT_DYNAMIC:
        # Dynamic claim without known lease expiry.
        return STATE_DYNAMIC
    if host.last_seen is not None:
        return STATE_OBSERVED
    return STATE_UNKNOWN


def allocation_label(state):
    """Return the human readable label for a derived allocation state."""
    return ALLOCATION_STATE_LABELS.get(state, state)


#: CSV column headers for the assignment/lease/observation-provenance
#: fields in import/export files (``last_seen`` keeps its legacy column).
EXPORT_ASPECT_COLUMNS = {
    "assignment_type": "Assignment Type",
    "assignment_source": "Assignment Source",
    "assignment_last_confirmed_at": "Assignment Last Confirmed At",
    "lease_expires_at": "Lease Expires At",
    "lease_source": "Lease Source",
    "lease_observed_at": "Lease Observed At",
    "last_seen_source": "Last Seen Source",
}


def format_timestamp(value):
    """Return an ISO 8601 UTC string for a stored timestamp, or None."""
    value = to_api_utc(value)
    return value.isoformat() if value is not None else None


def export_aspect_values(host):
    """Return the exportable aspect fields of a host (JSON-safe)."""
    values = {}
    for field in EXPORT_ASPECT_COLUMNS:
        value = getattr(host, field)
        if field in TIMESTAMP_FIELDS:
            value = format_timestamp(value)
        values[field] = value
    return values


def normalize_imported_aspects(host_data):
    """Validate imported aspect fields in place.

    Empty strings become ``None``. Raises ``ValueError`` on invalid
    values.
    """
    for field in EXPORT_ASPECT_COLUMNS:
        if field not in host_data:
            continue
        value = host_data[field]
        if isinstance(value, str):
            value = value.strip()
        host_data[field] = (
            None if value in ("", None) else parse_aspect_field(field, value)
        )
