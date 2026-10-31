"""Host API endpoints."""

import ipaddress

from flask import current_app, request
from flask_restx import Namespace, Resource, fields

from ipam.allocation import (
    ASPECT_FIELDS,
    ASPECT_FRESHNESS_FIELD,
    ASSIGNMENT_TYPES,
    PERSISTENT_ASSIGNMENT_TYPES,
    normalize_mac,
    parse_aspect_field,
    parse_timestamp,
    to_api_utc,
)
from ipam.api.models import (
    error_model,
    host_input_model,
    host_model,
    pagination_model,
)
from ipam.extensions import db
from ipam.models import Host, Network
from ipam.normalize import strip_domain_suffix

api = Namespace("hosts", description="Host management operations")

# Register models
host = api.model("Host", host_model)
host_input = api.model("HostInput", host_input_model)
pagination = api.model("Pagination", pagination_model)
error = api.model("Error", error_model)

# Paginated response model
host_list = api.model(
    "HostList",
    {
        "data": fields.List(fields.Nested(host)),
        "pagination": fields.Nested(pagination),
    },
)


def _parse_bool(value):
    """Parse boolean-like values from API inputs."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError("Expected a boolean value")


def _parse_datetime(value):
    """Parse a legacy ISO 8601 timestamp (naive input treated as UTC)."""
    return parse_timestamp(value, require_timezone=False)


ASPECT_FIELD_NAMES = tuple(
    f for fields_ in ASPECT_FIELDS.values() for f in fields_
)


def _parse_aspect_fields(data):
    """Validate the assignment/lease/observation fields present in ``data``.

    Returns a dict containing only the fields present in the request,
    normalized for storage. Explicit ``null`` is kept as ``None`` (clear).

    Raises:
        ValueError: A field has an invalid value.
    """
    parsed = {}
    for field in ASPECT_FIELD_NAMES:
        if field in data:
            parsed[field] = parse_aspect_field(field, data[field])
    return parsed


def serialize_host(h):
    """Return the API representation of a host."""
    return {
        "id": h.id,
        "ip_address": h.ip_address,
        "hostname": h.hostname,
        "cname": h.cname,
        "mac_address": h.mac_address,
        "status": h.status,
        "is_assigned": h.is_assigned,
        "last_seen": to_api_utc(h.last_seen),
        "discovery_source": h.discovery_source,
        "description": h.description,
        "network_id": h.network_id,
        "network": (
            f"{h.network_ref.network}/{h.network_ref.cidr}"
            if h.network_ref
            else None
        ),
        "assignment_type": h.assignment_type,
        "assignment_source": h.assignment_source,
        "assignment_last_confirmed_at": to_api_utc(
            h.assignment_last_confirmed_at
        ),
        "lease_expires_at": to_api_utc(h.lease_expires_at),
        "lease_source": h.lease_source,
        "lease_observed_at": to_api_utc(h.lease_observed_at),
        "last_seen_source": h.last_seen_source,
        "lease_active": h.lease_active,
        "allocation_state": h.allocation_state,
        "allocation_label": h.allocation_label,
    }


def _is_older(incoming, stored):
    """True if an incoming freshness timestamp predates the stored one."""
    return incoming is not None and stored is not None and incoming < stored


def apply_aspect_upsert(host_obj, parsed, created):
    """Apply assignment/lease/observation fields with reconciliation rules.

    Each aspect is applied independently, so updating or clearing one
    never touches the other two. For an existing host:

    * An aspect whose freshness timestamp (``assignment_last_confirmed_at``,
      ``lease_observed_at``, ``last_seen``) is older than the stored one
      is ignored as a whole, so older data never replaces newer data.
    * A persistent assignment (reservation/static) is never replaced by
      ``dynamic`` or ``unknown``; it can only be changed to another
      persistent type or cleared with an explicit ``null``.

    Returns:
        A sorted list of aspect names that were ignored.
    """
    ignored = []
    for aspect, fields_ in ASPECT_FIELDS.items():
        present = {f: parsed[f] for f in fields_ if f in parsed}
        if not present:
            continue
        if not created:
            freshness = ASPECT_FRESHNESS_FIELD[aspect]
            if freshness in present and _is_older(
                present[freshness], getattr(host_obj, freshness)
            ):
                ignored.append(aspect)
                continue
            new_type = present.get("assignment_type")
            if (
                aspect == "assignment"
                and "assignment_type" in present
                and new_type is not None
                and new_type not in PERSISTENT_ASSIGNMENT_TYPES
                and host_obj.assignment_type in PERSISTENT_ASSIGNMENT_TYPES
            ):
                ignored.append(aspect)
                continue
        for field, value in present.items():
            setattr(host_obj, field, value)
    return sorted(ignored)


@api.route("")
class HostList(Resource):
    @api.doc("list_hosts")
    @api.marshal_with(host_list)
    @api.param("page", "Page number", type=int, default=1)
    @api.param("per_page", "Items per page", type=int, default=50)
    @api.param("hostname", "Filter by hostname (wildcard supported)")
    @api.param("cname", "Filter by CNAME")
    @api.param("status", "Filter by status (active, inactive, reserved)")
    @api.param("is_assigned", "Filter by assignment status", type=bool)
    @api.param("mac_address", "Filter by MAC address")
    @api.param("network_id", "Filter by network ID", type=int)
    @api.param(
        "assignment_type",
        "Filter by assignment type ("
        + ", ".join(ASSIGNMENT_TYPES)
        + ", or 'unset')",
    )
    def get(self):
        """List all hosts with optional filtering."""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        query = Host.query

        # Apply filters
        if hostname := request.args.get("hostname"):
            query = query.filter(Host.hostname.ilike(f"%{hostname}%"))
        if cname := request.args.get("cname"):
            query = query.filter(Host.cname.ilike(f"%{cname}%"))
        if status := request.args.get("status"):
            query = query.filter(Host.status == status)
        if "is_assigned" in request.args:
            try:
                is_assigned = _parse_bool(request.args.get("is_assigned"))
            except ValueError as e:
                api.abort(400, str(e))
            query = query.filter(Host.is_assigned == is_assigned)
        if mac_address := request.args.get("mac_address"):
            query = query.filter(Host.mac_address == mac_address)
        if network_id := request.args.get("network_id", type=int):
            query = query.filter(Host.network_id == network_id)
        if assignment_type := request.args.get("assignment_type"):
            if assignment_type == "unset":
                query = query.filter(Host.assignment_type.is_(None))
            elif assignment_type in ASSIGNMENT_TYPES:
                query = query.filter(Host.assignment_type == assignment_type)
            else:
                api.abort(400, f"Invalid assignment_type: {assignment_type}")

        # Paginate results
        pagination_obj = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "data": [serialize_host(h) for h in pagination_obj.items],
            "pagination": {
                "page": pagination_obj.page,
                "per_page": pagination_obj.per_page,
                "total_items": pagination_obj.total,
                "total_pages": pagination_obj.pages,
            },
        }

    @api.doc("create_host")
    @api.expect(host_input, validate=True)
    @api.marshal_with(host, code=201)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create a new host."""
        data = request.json

        # Validate IP address
        try:
            ipaddress.IPv4Address(data["ip_address"])
        except ValueError as e:
            api.abort(400, f"Invalid IP address: {e}")

        # Check for duplicate
        existing = Host.query.filter_by(ip_address=data["ip_address"]).first()
        if existing:
            api.abort(400, "IP address already exists")

        # Auto-detect network if not provided
        network_id = data.get("network_id")
        if network_id:
            network = Network.query.get(network_id)
        else:
            network = Network.find_for_ip(data["ip_address"])
            network_id = network.id if network else None

        # Create host
        try:
            aspects = _parse_aspect_fields(data)
            is_assigned = _parse_bool(data.get("is_assigned"))
        except ValueError as e:
            api.abort(400, str(e))

        if is_assigned is None:
            is_assigned = current_app.config.get("HOST_ASSIGN_ON_CREATE", True)

        host_obj = Host(
            ip_address=data["ip_address"],
            hostname=strip_domain_suffix(
                data.get("hostname"), network.domain if network else None
            ),
            cname=data.get("cname"),
            mac_address=data.get("mac_address"),
            status=data.get("status", "active"),
            is_assigned=is_assigned,
            discovery_source=data.get("discovery_source"),
            description=data.get("description"),
            network_id=network_id,
            **aspects,
        )

        db.session.add(host_obj)
        db.session.commit()

        return serialize_host(host_obj), 201


HOST_UPSERT_FIELDS = (
    "hostname",
    "cname",
    "mac_address",
    "status",
    "description",
)


@api.route("/upsert")
class HostUpsert(Resource):
    @api.doc("upsert_host")
    @api.expect(host_input)
    @api.marshal_with(host)
    @api.response(200, "Host updated", host)
    @api.response(201, "Host created", host)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create or update a host by its IP address.

        Matches an existing host by ``ip_address``. Only fields present
        in the request body are changed; fields left out of the body
        are kept as-is on an existing host. Sending a field with an
        explicit null clears it. ``network_id`` is auto-detected from
        the IP address when a new host is created without one.

        Validation here is intentionally manual (no ``validate=True``)
        rather than schema-based: schema validation would reject an
        explicit ``null`` on a typed field, which upsert relies on to
        clear it.

        Assignment, lease and observation fields are reconciled per
        aspect (see :func:`apply_aspect_upsert`): stale updates and
        attempts to replace a reservation/static assignment with
        ``dynamic``/``unknown`` are ignored and reported in the
        ``X-IPAM-Ignored-Aspects`` response header. Changing the MAC of a
        host with a persistent assignment returns 409 unless
        ``confirm_mac_change`` is true; a confirmed change clears lease
        and observation data not supplied in the same request.
        """
        data = request.json or {}

        if "ip_address" not in data:
            api.abort(400, "ip_address is required")

        try:
            ipaddress.IPv4Address(data["ip_address"])
        except (TypeError, ValueError) as e:
            api.abort(400, f"Invalid IP address: {e}")

        # Validate everything before touching the database.
        try:
            aspects = _parse_aspect_fields(data)
            is_assigned = (
                _parse_bool(data.get("is_assigned"))
                if "is_assigned" in data
                else None
            )
            confirm_mac_change = bool(
                _parse_bool(data.get("confirm_mac_change"))
            )
        except ValueError as e:
            api.abort(400, str(e))

        host_obj = Host.query.filter_by(ip_address=data["ip_address"]).first()
        created = host_obj is None

        mac_changed = False
        if not created and "mac_address" in data:
            old_mac = normalize_mac(host_obj.mac_address)
            new_mac = normalize_mac(data.get("mac_address"))
            mac_changed = bool(old_mac and new_mac and old_mac != new_mac)
            if (
                mac_changed
                and host_obj.assignment_type in PERSISTENT_ASSIGNMENT_TYPES
                and not confirm_mac_change
            ):
                api.abort(
                    409,
                    f"MAC address conflict for {host_obj.ip_address}: "
                    f"the {host_obj.assignment_type} assignment belongs to "
                    f"{host_obj.mac_address}, request has "
                    f"{data.get('mac_address')}. Send "
                    "confirm_mac_change=true to transition deliberately.",
                    existing_mac_address=host_obj.mac_address,
                    requested_mac_address=data.get("mac_address"),
                    assignment_type=host_obj.assignment_type,
                )

        if created:
            host_obj = Host(ip_address=data["ip_address"], status="active")
            db.session.add(host_obj)

        # Resolve the network first so its domain is known for hostname
        # suffix stripping below.
        if "network_id" in data:
            network_id = data.get("network_id")
            network = Network.query.get(network_id) if network_id else None
            host_obj.network_id = network_id
        elif created:
            network = Network.find_for_ip(data["ip_address"])
            host_obj.network_id = network.id if network else None
        else:
            network = (
                Network.query.get(host_obj.network_id)
                if host_obj.network_id
                else None
            )

        for field in HOST_UPSERT_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if field == "hostname":
                value = strip_domain_suffix(
                    value, network.domain if network else None
                )
            setattr(host_obj, field, value)

        if is_assigned is not None:
            host_obj.is_assigned = is_assigned
        elif created:
            host_obj.is_assigned = current_app.config.get(
                "HOST_ASSIGN_ON_CREATE", True
            )

        if "discovery_source" in data:
            host_obj.discovery_source = data.get("discovery_source")

        if mac_changed and confirm_mac_change:
            # Deliberate device transition: lease and observation history
            # belonged to the previous device and must not carry over.
            for field in ASPECT_FIELDS["lease"] + ASPECT_FIELDS["observation"]:
                if field not in aspects:
                    setattr(host_obj, field, None)

        ignored = apply_aspect_upsert(host_obj, aspects, created)

        db.session.commit()

        headers = {}
        if ignored:
            headers["X-IPAM-Ignored-Aspects"] = ",".join(ignored)
        return serialize_host(host_obj), 201 if created else 200, headers


@api.route("/<int:id>")
@api.param("id", "The host identifier")
class HostResource(Resource):
    @api.doc("get_host")
    @api.marshal_with(host)
    @api.response(404, "Host not found")
    def get(self, id):
        """Get a specific host by ID."""
        host_obj = Host.query.get_or_404(id)
        return serialize_host(host_obj)

    @api.doc("update_host")
    @api.expect(host_input, validate=True)
    @api.marshal_with(host)
    @api.response(404, "Host not found")
    @api.response(400, "Validation Error", error)
    def put(self, id):
        """Update a host."""
        host_obj = Host.query.get_or_404(id)
        data = request.json

        # Validate IP address if changed
        if data["ip_address"] != host_obj.ip_address:
            try:
                ipaddress.IPv4Address(data["ip_address"])
            except ValueError as e:
                api.abort(400, f"Invalid IP address: {e}")

            # Check for duplicate
            existing = (
                Host.query.filter_by(ip_address=data["ip_address"])
                .filter(Host.id != id)
                .first()
            )
            if existing:
                api.abort(400, "IP address already exists")

        # Auto-detect network if IP changed and network_id not provided
        network_id = data.get("network_id", host_obj.network_id)
        if data["ip_address"] != host_obj.ip_address and not data.get(
            "network_id"
        ):
            network = Network.find_for_ip(data["ip_address"])
            network_id = network.id if network else None
        else:
            network = Network.query.get(network_id) if network_id else None

        # Update fields. Assignment, lease and observation fields are
        # only changed when present in the body, so legacy clients that
        # do not know them leave them untouched. PUT is an explicit
        # manual update: freshness and persistence guards of the upsert
        # endpoint do not apply here.
        try:
            aspects = _parse_aspect_fields(data)
            is_assigned = _parse_bool(data.get("is_assigned"))
        except ValueError as e:
            api.abort(400, str(e))

        host_obj.ip_address = data["ip_address"]
        host_obj.hostname = strip_domain_suffix(
            data.get("hostname"), network.domain if network else None
        )
        host_obj.cname = data.get("cname")
        host_obj.mac_address = data.get("mac_address")
        host_obj.status = data.get("status", "active")
        if is_assigned is not None:
            host_obj.is_assigned = is_assigned
        for field, value in aspects.items():
            setattr(host_obj, field, value)
        if "discovery_source" in data:
            host_obj.discovery_source = data.get("discovery_source")
        host_obj.description = data.get("description")
        host_obj.network_id = network_id

        db.session.commit()

        return serialize_host(host_obj)

    @api.doc("delete_host")
    @api.response(204, "Host deleted")
    @api.response(404, "Host not found")
    def delete(self, id):
        """Delete a host."""
        host_obj = Host.query.get_or_404(id)

        db.session.delete(host_obj)
        db.session.commit()

        return "", 204
