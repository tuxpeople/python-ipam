"""API models for request/response serialization."""

from flask_restx import fields

# Network models
network_model = {
    "id": fields.Integer(readonly=True, description="Network ID"),
    "network": fields.String(
        required=True, description="Network address (e.g., 192.168.1.0)"
    ),
    "cidr": fields.Integer(
        required=True, description="CIDR notation (e.g., 24)", min=0, max=32
    ),
    "broadcast_address": fields.String(
        readonly=True, description="Broadcast address"
    ),
    "name": fields.String(description="Network name"),
    "domain": fields.String(description="DNS domain"),
    "vlan_id": fields.Integer(description="VLAN ID"),
    "description": fields.String(description="Network description"),
    "location": fields.String(description="Physical location"),
    "total_hosts": fields.Integer(
        readonly=True, description="Total available hosts"
    ),
    "used_hosts": fields.Integer(readonly=True, description="Used hosts"),
    "available_hosts": fields.Integer(
        readonly=True, description="Available hosts"
    ),
}

network_input_model = {
    "network": fields.String(
        required=True, description="Network address (e.g., 192.168.1.0)"
    ),
    "cidr": fields.Integer(
        required=True, description="CIDR notation (e.g., 24)", min=0, max=32
    ),
    "name": fields.String(description="Network name"),
    "domain": fields.String(description="DNS domain"),
    "vlan_id": fields.Integer(description="VLAN ID"),
    "description": fields.String(description="Network description"),
    "location": fields.String(description="Physical location"),
}

# DHCP range models
dhcp_range_model = {
    "id": fields.Integer(readonly=True, description="DHCP range ID"),
    "network_id": fields.Integer(description="Associated network ID"),
    "start_ip": fields.String(
        required=True, description="Range start IP address"
    ),
    "end_ip": fields.String(required=True, description="Range end IP address"),
    "description": fields.String(description="Range description"),
    "is_active": fields.Boolean(description="Whether the range is active"),
}

dhcp_range_input_model = {
    "network_id": fields.Integer(required=True, description="Network ID"),
    "start_ip": fields.String(
        required=True, description="Range start IP address"
    ),
    "end_ip": fields.String(required=True, description="Range end IP address"),
    "description": fields.String(description="Range description"),
    "is_active": fields.Boolean(description="Whether the range is active"),
}

# Host models
host_model = {
    "id": fields.Integer(readonly=True, description="Host ID"),
    "ip_address": fields.String(
        required=True, description="IP address (e.g., 192.168.1.100)"
    ),
    "hostname": fields.String(description="Hostname"),
    "cname": fields.String(description="CNAME alias"),
    "mac_address": fields.String(
        description="MAC address (e.g., aa:bb:cc:dd:ee:ff)"
    ),
    "status": fields.String(
        description="Host status (active, inactive, reserved)"
    ),
    "is_assigned": fields.Boolean(
        description="Whether the host is officially assigned"
    ),
    "last_seen": fields.DateTime(
        description="Last observed timestamp (ISO 8601)"
    ),
    "discovery_source": fields.String(
        description="Discovery source identifier"
    ),
    "description": fields.String(description="Host description"),
    "network_id": fields.Integer(description="Associated network ID"),
    "network": fields.String(readonly=True, description="Network address"),
}

host_input_model = {
    "ip_address": fields.String(
        required=True, description="IP address (e.g., 192.168.1.100)"
    ),
    "hostname": fields.String(description="Hostname"),
    "cname": fields.String(description="CNAME alias"),
    "mac_address": fields.String(
        description="MAC address (e.g., aa:bb:cc:dd:ee:ff)"
    ),
    "status": fields.String(
        description="Host status (active, inactive, reserved)"
    ),
    "is_assigned": fields.Boolean(
        description="Whether the host is officially assigned"
    ),
    "last_seen": fields.DateTime(
        description="Last observed timestamp (ISO 8601)"
    ),
    "discovery_source": fields.String(
        description="Discovery source identifier"
    ),
    "description": fields.String(description="Host description"),
    "network_id": fields.Integer(description="Associated network ID"),
}

# IP management models
next_ip_model = {
    "ip_address": fields.String(description="Next available IP address"),
    "network": fields.String(description="Network address"),
    "network_id": fields.Integer(description="Network ID"),
}

available_ips_model = {
    "network": fields.String(description="Network address"),
    "network_id": fields.Integer(description="Network ID"),
    "total_available": fields.Integer(description="Total available IPs"),
    "available_ips": fields.List(
        fields.String, description="List of available IP addresses"
    ),
}

# Pagination models
pagination_model = {
    "page": fields.Integer(description="Current page number"),
    "per_page": fields.Integer(description="Items per page"),
    "total_items": fields.Integer(description="Total number of items"),
    "total_pages": fields.Integer(description="Total number of pages"),
}

# Error models
error_model = {
    "message": fields.String(description="Error message"),
    "errors": fields.Raw(description="Detailed error information"),
}
