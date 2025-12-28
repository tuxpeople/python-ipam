"""Network API endpoints."""

import ipaddress

from flask import request
from flask_restx import Namespace, Resource, fields

from ipam.extensions import db
from ipam.models import DhcpRange, Network
from ipam.api.models import (
    dhcp_range_model,
    dhcp_range_input_model,
    network_model,
    network_input_model,
    pagination_model,
    error_model,
)

api = Namespace("networks", description="Network management operations")

# Register models
network = api.model("Network", network_model)
network_input = api.model("NetworkInput", network_input_model)
pagination = api.model("Pagination", pagination_model)
error = api.model("Error", error_model)

# Paginated response model
network_list = api.model(
    "NetworkList",
    {
        "data": fields.List(fields.Nested(network)),
        "pagination": fields.Nested(pagination),
    },
)

# DHCP range models
dhcp_range = api.model("DhcpRange", dhcp_range_model)
dhcp_range_input = api.model("DhcpRangeInput", dhcp_range_input_model)
dhcp_range_input_network = api.model(
    "DhcpRangeInputNetwork",
    {
        "start_ip": fields.String(
            required=True, description="Range start IP address"
        ),
        "end_ip": fields.String(
            required=True, description="Range end IP address"
        ),
        "description": fields.String(description="Range description"),
        "is_active": fields.Boolean(description="Whether the range is active"),
    },
)

dhcp_range_list = api.model(
    "DhcpRangeList",
    {"data": fields.List(fields.Nested(dhcp_range))},
)


@api.route("")
class NetworkList(Resource):
    @api.doc("list_networks")
    @api.marshal_with(network_list)
    @api.param("page", "Page number", type=int, default=1)
    @api.param("per_page", "Items per page", type=int, default=50)
    @api.param("name", "Filter by network name")
    @api.param("domain", "Filter by domain")
    @api.param("vlan_id", "Filter by VLAN ID", type=int)
    @api.param("location", "Filter by location")
    def get(self):
        """List all networks with optional filtering."""

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        query = Network.query

        # Apply filters
        if name := request.args.get("name"):
            query = query.filter(Network.name.ilike(f"%{name}%"))
        if domain := request.args.get("domain"):
            query = query.filter(Network.domain.ilike(f"%{domain}%"))
        if vlan_id := request.args.get("vlan_id", type=int):
            query = query.filter(Network.vlan_id == vlan_id)
        if location := request.args.get("location"):
            query = query.filter(Network.location.ilike(f"%{location}%"))

        # Paginate results
        pagination_obj = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "data": [
                {
                    "id": n.id,
                    "network": n.network,
                    "cidr": n.cidr,
                    "broadcast_address": n.broadcast_address,
                    "name": n.name,
                    "domain": n.domain,
                    "vlan_id": n.vlan_id,
                    "description": n.description,
                    "location": n.location,
                    "total_hosts": n.total_hosts,
                    "used_hosts": n.used_hosts,
                    "available_hosts": n.available_hosts,
                }
                for n in pagination_obj.items
            ],
            "pagination": {
                "page": pagination_obj.page,
                "per_page": pagination_obj.per_page,
                "total_items": pagination_obj.total,
                "total_pages": pagination_obj.pages,
            },
        }

    @api.doc("create_network")
    @api.expect(network_input, validate=True)
    @api.marshal_with(network, code=201)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create a new network."""

        data = request.json

        # Validate network address
        try:
            net = ipaddress.IPv4Network(
                f"{data['network']}/{data['cidr']}", strict=False
            )
            broadcast = str(net.broadcast_address)
        except ValueError as e:
            api.abort(400, f"Invalid network address: {e}")

        # Check for duplicate
        existing = Network.query.filter_by(network=data["network"]).first()
        if existing:
            api.abort(400, "Network already exists")

        # Create network
        network_obj = Network(
            network=data["network"],
            cidr=data["cidr"],
            broadcast_address=broadcast,
            name=data.get("name"),
            domain=data.get("domain"),
            vlan_id=data.get("vlan_id"),
            description=data.get("description"),
            location=data.get("location"),
        )

        db.session.add(network_obj)
        db.session.commit()

        return {
            "id": network_obj.id,
            "network": network_obj.network,
            "cidr": network_obj.cidr,
            "broadcast_address": network_obj.broadcast_address,
            "name": network_obj.name,
            "domain": network_obj.domain,
            "vlan_id": network_obj.vlan_id,
            "description": network_obj.description,
            "location": network_obj.location,
            "total_hosts": network_obj.total_hosts,
            "used_hosts": network_obj.used_hosts,
            "available_hosts": network_obj.available_hosts,
        }, 201


@api.route("/<int:id>")
@api.param("id", "The network identifier")
class NetworkResource(Resource):
    @api.doc("get_network")
    @api.marshal_with(network)
    @api.response(404, "Network not found")
    def get(self, id):
        """Get a specific network by ID."""
        network_obj = Network.query.get_or_404(id)
        return {
            "id": network_obj.id,
            "network": network_obj.network,
            "cidr": network_obj.cidr,
            "broadcast_address": network_obj.broadcast_address,
            "name": network_obj.name,
            "domain": network_obj.domain,
            "vlan_id": network_obj.vlan_id,
            "description": network_obj.description,
            "location": network_obj.location,
            "total_hosts": network_obj.total_hosts,
            "used_hosts": network_obj.used_hosts,
            "available_hosts": network_obj.available_hosts,
        }

    @api.doc("update_network")
    @api.expect(network_input, validate=True)
    @api.marshal_with(network)
    @api.response(404, "Network not found")
    @api.response(400, "Validation Error", error)
    def put(self, id):
        """Update a network."""
        network_obj = Network.query.get_or_404(id)
        data = request.json

        # Validate network address if changed
        if (
            data["network"] != network_obj.network
            or data["cidr"] != network_obj.cidr
        ):
            try:
                net = ipaddress.IPv4Network(
                    f"{data['network']}/{data['cidr']}", strict=False
                )
                network_obj.broadcast_address = str(net.broadcast_address)
            except ValueError as e:
                api.abort(400, f"Invalid network address: {e}")

            # Check for duplicate
            existing = (
                Network.query.filter_by(network=data["network"])
                .filter(Network.id != id)
                .first()
            )
            if existing:
                api.abort(400, "Network already exists")

        # Update fields
        network_obj.network = data["network"]
        network_obj.cidr = data["cidr"]
        network_obj.name = data.get("name")
        network_obj.domain = data.get("domain")
        network_obj.vlan_id = data.get("vlan_id")
        network_obj.description = data.get("description")
        network_obj.location = data.get("location")

        db.session.commit()

        return {
            "id": network_obj.id,
            "network": network_obj.network,
            "cidr": network_obj.cidr,
            "broadcast_address": network_obj.broadcast_address,
            "name": network_obj.name,
            "domain": network_obj.domain,
            "vlan_id": network_obj.vlan_id,
            "description": network_obj.description,
            "location": network_obj.location,
            "total_hosts": network_obj.total_hosts,
            "used_hosts": network_obj.used_hosts,
            "available_hosts": network_obj.available_hosts,
        }

    @api.doc("delete_network")
    @api.response(204, "Network deleted")
    @api.response(404, "Network not found")
    @api.response(400, "Cannot delete network with assigned hosts", error)
    def delete(self, id):
        """Delete a network."""
        network_obj = Network.query.get_or_404(id)

        # Check for assigned hosts
        if network_obj.hosts:
            api.abort(
                400,
                f"Cannot delete network with {len(network_obj.hosts)} "
                f"assigned hosts",
            )

        db.session.delete(network_obj)
        db.session.commit()

        return "", 204


@api.route("/<int:id>/hosts")
@api.param("id", "The network identifier")
class NetworkHosts(Resource):
    @api.doc("get_network_hosts")
    @api.response(404, "Network not found")
    def get(self, id):
        """Get all hosts in a specific network."""
        network_obj = Network.query.get_or_404(id)
        return {
            "network_id": network_obj.id,
            "network": f"{network_obj.network}/{network_obj.cidr}",
            "hosts": [
                {
                    "id": h.id,
                    "ip_address": h.ip_address,
                    "hostname": h.hostname,
                    "cname": h.cname,
                    "mac_address": h.mac_address,
                    "status": h.status,
                    "description": h.description,
                }
                for h in network_obj.hosts
            ],
        }


@api.route("/<int:id>/dhcp-ranges")
@api.param("id", "The network identifier")
class NetworkDhcpRanges(Resource):
    @api.doc("get_network_dhcp_ranges")
    @api.marshal_with(dhcp_range_list)
    @api.response(404, "Network not found")
    def get(self, id):
        """Get DHCP ranges for a specific network."""
        network_obj = Network.query.get_or_404(id)
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
                for r in network_obj.dhcp_ranges
            ]
        }

    @api.doc("create_network_dhcp_range")
    @api.expect(dhcp_range_input_network, validate=True)
    @api.marshal_with(dhcp_range, code=201)
    @api.response(400, "Validation Error", error)
    def post(self, id):
        """Create a DHCP range for a network."""
        network_obj = Network.query.get_or_404(id)
        data = request.json

        try:
            start_ip = ipaddress.IPv4Address(data["start_ip"])
            end_ip = ipaddress.IPv4Address(data["end_ip"])
        except ValueError as e:
            api.abort(400, f"Invalid IP address: {e}")

        net = ipaddress.IPv4Network(
            f"{network_obj.network}/{network_obj.cidr}", strict=False
        )
        if start_ip not in net or end_ip not in net:
            api.abort(400, "DHCP range must be within the selected network")
        if start_ip > end_ip:
            api.abort(400, "Start IP must be less than or equal to End IP")

        for existing in DhcpRange.query.filter_by(
            network_id=network_obj.id
        ).all():
            existing_start = ipaddress.IPv4Address(existing.start_ip)
            existing_end = ipaddress.IPv4Address(existing.end_ip)
            overlaps = not (end_ip < existing_start or start_ip > existing_end)
            if overlaps:
                api.abort(
                    400,
                    "DHCP range overlaps an existing range: "
                    f"{existing.start_ip}-{existing.end_ip}",
                )

        range_obj = DhcpRange(
            network_id=network_obj.id,
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
