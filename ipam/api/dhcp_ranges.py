"""DHCP range API endpoints."""

import ipaddress

from flask import request
from flask_restx import Namespace, Resource, fields

from ipam.api.models import (
    dhcp_range_input_model,
    dhcp_range_model,
    error_model,
    pagination_model,
)
from ipam.extensions import db
from ipam.models import DhcpRange, Network

api = Namespace("dhcp-ranges", description="DHCP range operations")

# Register models
dhcp_range = api.model("DhcpRange", dhcp_range_model)
dhcp_range_input = api.model("DhcpRangeInput", dhcp_range_input_model)
pagination = api.model("Pagination", pagination_model)
error = api.model("Error", error_model)

# Paginated response model
dhcp_range_list = api.model(
    "DhcpRangeList",
    {
        "data": fields.List(fields.Nested(dhcp_range)),
        "pagination": fields.Nested(pagination),
    },
)


def _validate_range(network, start_ip, end_ip, exclude_range_id=None):
    """Validate DHCP range boundaries and overlaps."""
    net = ipaddress.IPv4Network(
        f"{network.network}/{network.cidr}", strict=False
    )
    if start_ip not in net or end_ip not in net:
        return "DHCP range must be within the selected network"
    if start_ip > end_ip:
        return "Start IP must be less than or equal to End IP"

    query = DhcpRange.query.filter_by(network_id=network.id)
    if exclude_range_id:
        query = query.filter(DhcpRange.id != exclude_range_id)
    for existing in query.all():
        existing_start = ipaddress.IPv4Address(existing.start_ip)
        existing_end = ipaddress.IPv4Address(existing.end_ip)
        overlaps = not (end_ip < existing_start or start_ip > existing_end)
        if overlaps:
            return (
                "DHCP range overlaps an existing range: "
                f"{existing.start_ip}-{existing.end_ip}"
            )
    return None


@api.route("")
class DhcpRangeList(Resource):
    @api.doc("list_dhcp_ranges")
    @api.marshal_with(dhcp_range_list)
    @api.param("page", "Page number", type=int, default=1)
    @api.param("per_page", "Items per page", type=int, default=50)
    @api.param("network_id", "Filter by network ID", type=int)
    def get(self):
        """List all DHCP ranges with optional filtering."""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        query = DhcpRange.query
        if network_id := request.args.get("network_id", type=int):
            query = query.filter(DhcpRange.network_id == network_id)

        pagination_obj = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "data": [
                {
                    "id": r.id,
                    "network_id": r.network_id,
                    "start_ip": r.start_ip,
                    "end_ip": r.end_ip,
                    "description": r.description,
                    "is_active": r.is_active,
                }
                for r in pagination_obj.items
            ],
            "pagination": {
                "page": pagination_obj.page,
                "per_page": pagination_obj.per_page,
                "total_items": pagination_obj.total,
                "total_pages": pagination_obj.pages,
            },
        }

    @api.doc("create_dhcp_range")
    @api.expect(dhcp_range_input, validate=True)
    @api.marshal_with(dhcp_range, code=201)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create a new DHCP range."""
        data = request.json

        network = Network.query.get_or_404(data["network_id"])

        try:
            start_ip = ipaddress.IPv4Address(data["start_ip"])
            end_ip = ipaddress.IPv4Address(data["end_ip"])
        except ValueError as e:
            api.abort(400, f"Invalid IP address: {e}")

        error_message = _validate_range(network, start_ip, end_ip)
        if error_message:
            api.abort(400, error_message)

        range_obj = DhcpRange(
            network_id=network.id,
            start_ip=str(start_ip),
            end_ip=str(end_ip),
            description=data.get("description"),
            is_active=data.get("is_active", True),
        )
        db.session.add(range_obj)
        db.session.commit()

        return {
            "id": range_obj.id,
            "network_id": range_obj.network_id,
            "start_ip": range_obj.start_ip,
            "end_ip": range_obj.end_ip,
            "description": range_obj.description,
            "is_active": range_obj.is_active,
        }, 201


@api.route("/upsert")
class DhcpRangeUpsert(Resource):
    @api.doc("upsert_dhcp_range")
    @api.expect(dhcp_range_input)
    @api.marshal_with(dhcp_range)
    @api.response(200, "DHCP range updated", dhcp_range)
    @api.response(201, "DHCP range created", dhcp_range)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create or update a DHCP range by network and start IP.

        Matches an existing range by ``(network_id, start_ip)``. If
        ``network_id`` is omitted, it is auto-detected from
        ``start_ip``. ``start_ip`` and ``end_ip`` are always required
        since they define the range itself; ``description`` is a
        patchable field left as-is when omitted, and an explicit null
        clears it.

        Validation here is intentionally manual (no ``validate=True``)
        rather than schema-based: schema validation would reject an
        explicit ``null`` on a typed field, which upsert relies on to
        clear it.
        """
        data = request.json or {}

        if "start_ip" not in data or "end_ip" not in data:
            api.abort(400, "start_ip and end_ip are required")

        try:
            start_ip = ipaddress.IPv4Address(data["start_ip"])
            end_ip = ipaddress.IPv4Address(data["end_ip"])
        except (TypeError, ValueError) as e:
            api.abort(400, f"Invalid IP address: {e}")

        if data.get("network_id") is not None:
            network = Network.query.get_or_404(data["network_id"])
        else:
            network = Network.find_for_ip(str(start_ip))
            if network is None:
                api.abort(
                    400,
                    "No network contains start_ip; specify network_id "
                    "explicitly",
                )

        range_obj = DhcpRange.query.filter_by(
            network_id=network.id, start_ip=str(start_ip)
        ).first()
        created = range_obj is None

        error_message = _validate_range(
            network,
            start_ip,
            end_ip,
            exclude_range_id=None if created else range_obj.id,
        )
        if error_message:
            api.abort(400, error_message)

        if created:
            range_obj = DhcpRange(network_id=network.id, start_ip=str(start_ip))
            db.session.add(range_obj)

        range_obj.end_ip = str(end_ip)

        if "description" in data:
            range_obj.description = data["description"]

        if "is_active" in data and data["is_active"] is not None:
            range_obj.is_active = bool(data["is_active"])
        elif created:
            range_obj.is_active = True

        db.session.commit()

        return {
            "id": range_obj.id,
            "network_id": range_obj.network_id,
            "start_ip": range_obj.start_ip,
            "end_ip": range_obj.end_ip,
            "description": range_obj.description,
            "is_active": range_obj.is_active,
        }, 201 if created else 200


@api.route("/<int:id>")
@api.param("id", "The DHCP range identifier")
class DhcpRangeResource(Resource):
    @api.doc("get_dhcp_range")
    @api.marshal_with(dhcp_range)
    @api.response(404, "DHCP range not found")
    def get(self, id):
        """Get a DHCP range by ID."""
        range_obj = DhcpRange.query.get_or_404(id)
        return {
            "id": range_obj.id,
            "network_id": range_obj.network_id,
            "start_ip": range_obj.start_ip,
            "end_ip": range_obj.end_ip,
            "description": range_obj.description,
            "is_active": range_obj.is_active,
        }

    @api.doc("update_dhcp_range")
    @api.expect(dhcp_range_input, validate=True)
    @api.marshal_with(dhcp_range)
    @api.response(404, "DHCP range not found")
    @api.response(400, "Validation Error", error)
    def put(self, id):
        """Update a DHCP range."""
        range_obj = DhcpRange.query.get_or_404(id)
        data = request.json

        network = Network.query.get_or_404(data["network_id"])

        try:
            start_ip = ipaddress.IPv4Address(data["start_ip"])
            end_ip = ipaddress.IPv4Address(data["end_ip"])
        except ValueError as e:
            api.abort(400, f"Invalid IP address: {e}")

        error_message = _validate_range(
            network, start_ip, end_ip, exclude_range_id=range_obj.id
        )
        if error_message:
            api.abort(400, error_message)

        range_obj.network_id = network.id
        range_obj.start_ip = str(start_ip)
        range_obj.end_ip = str(end_ip)
        range_obj.description = data.get("description")
        range_obj.is_active = data.get("is_active", True)
        db.session.commit()

        return {
            "id": range_obj.id,
            "network_id": range_obj.network_id,
            "start_ip": range_obj.start_ip,
            "end_ip": range_obj.end_ip,
            "description": range_obj.description,
            "is_active": range_obj.is_active,
        }

    @api.doc("delete_dhcp_range")
    @api.response(204, "DHCP range deleted")
    @api.response(404, "DHCP range not found")
    def delete(self, id):
        """Delete a DHCP range."""
        range_obj = DhcpRange.query.get_or_404(id)
        db.session.delete(range_obj)
        db.session.commit()
        return "", 204
