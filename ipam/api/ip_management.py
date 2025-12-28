"""IP Management API endpoints."""

import ipaddress

from flask_restx import Namespace, Resource

from ipam.models import DhcpRange, Host, Network
from ipam.api.models import next_ip_model, available_ips_model, error_model

api = Namespace("ip", description="IP address management operations")

# Register models
next_ip = api.model("NextIP", next_ip_model)
available_ips = api.model("AvailableIPs", available_ips_model)
error = api.model("Error", error_model)


def _in_active_dhcp_range(ip_address, ranges):
    """Return True if IP is inside any active DHCP range."""
    for range_obj in ranges:
        if not range_obj.is_active:
            continue
        start_ip = ipaddress.IPv4Address(range_obj.start_ip)
        end_ip = ipaddress.IPv4Address(range_obj.end_ip)
        if start_ip <= ip_address <= end_ip:
            return True
    return False


@api.route("/networks/<int:network_id>/next-ip")
@api.param("network_id", "The network identifier")
class NextAvailableIP(Resource):
    @api.doc("get_next_ip")
    @api.marshal_with(next_ip)
    @api.response(404, "Network not found")
    @api.response(400, "No available IPs", error)
    def get(self, network_id):
        """Get the next available IP address in a network."""
        network = Network.query.get_or_404(network_id)

        # Get network range
        net = ipaddress.IPv4Network(
            f"{network.network}/{network.cidr}", strict=False
        )

        # Get all used IPs in this network
        used_ips = {
            ipaddress.IPv4Address(h.ip_address)
            for h in Host.query.filter_by(network_id=network_id).all()
        }
        dhcp_ranges = DhcpRange.query.filter_by(
            network_id=network_id, is_active=True
        ).all()

        # Find first available IP
        for ip in net.hosts():
            if ip in used_ips:
                continue
            if _in_active_dhcp_range(ip, dhcp_ranges):
                continue
            return {
                "ip_address": str(ip),
                "network": f"{network.network}/{network.cidr}",
                "network_id": network.id,
            }

        # No available IPs
        api.abort(400, "No available IP addresses in this network")


@api.route("/networks/<int:network_id>/available-ips")
@api.param("network_id", "The network identifier")
class AvailableIPs(Resource):
    @api.doc("get_available_ips")
    @api.marshal_with(available_ips)
    @api.response(404, "Network not found")
    @api.param("limit", "Limit number of IPs returned", type=int)
    def get(self, network_id):
        """Get all available IP addresses in a network."""
        network = Network.query.get_or_404(network_id)
        limit = api.payload.get("limit") if api.payload else None

        # Get network range
        net = ipaddress.IPv4Network(
            f"{network.network}/{network.cidr}", strict=False
        )

        # Get all used IPs in this network
        used_ips = {
            ipaddress.IPv4Address(h.ip_address)
            for h in Host.query.filter_by(network_id=network_id).all()
        }
        dhcp_ranges = DhcpRange.query.filter_by(
            network_id=network_id, is_active=True
        ).all()

        # Find all available IPs
        available = [
            str(ip)
            for ip in net.hosts()
            if ip not in used_ips and not _in_active_dhcp_range(ip, dhcp_ranges)
        ]

        # Apply limit if specified
        if limit:
            available = available[:limit]

        return {
            "network": f"{network.network}/{network.cidr}",
            "network_id": network.id,
            "total_available": len(available),
            "available_ips": available,
        }


@api.route("/<string:ip_address>")
@api.param("ip_address", "The IP address to query")
class IPQuery(Resource):
    @api.doc("query_ip")
    @api.response(404, "IP address not found")
    def get(self, ip_address):
        """Query IP address status and details."""
        # Validate IP address
        try:
            ip = ipaddress.IPv4Address(ip_address)
        except ValueError as e:
            api.abort(400, f"Invalid IP address: {e}")

        # Check if IP exists as host
        host = Host.query.filter_by(ip_address=ip_address).first()

        if host:
            return {
                "ip_address": ip_address,
                "status": "assigned",
                "host": {
                    "id": host.id,
                    "hostname": host.hostname,
                    "cname": host.cname,
                    "mac_address": host.mac_address,
                    "status": host.status,
                    "is_assigned": host.is_assigned,
                    "last_seen": host.last_seen,
                    "discovery_source": host.discovery_source,
                    "description": host.description,
                    "network_id": host.network_id,
                    "network": (
                        f"{host.network_ref.network}/{host.network_ref.cidr}"
                        if host.network_ref
                        else None
                    ),
                },
            }

        # Check which network this IP belongs to
        networks = Network.query.all()
        for network in networks:
            net = ipaddress.IPv4Network(
                f"{network.network}/{network.cidr}", strict=False
            )
            if ip in net:
                dhcp_range = None
                for range_obj in network.dhcp_ranges:
                    if not range_obj.is_active:
                        continue
                    start_ip = ipaddress.IPv4Address(range_obj.start_ip)
                    end_ip = ipaddress.IPv4Address(range_obj.end_ip)
                    if start_ip <= ip <= end_ip:
                        dhcp_range = range_obj
                        break

                if dhcp_range:
                    return {
                        "ip_address": ip_address,
                        "status": "dhcp",
                        "dhcp_range": {
                            "id": dhcp_range.id,
                            "start_ip": dhcp_range.start_ip,
                            "end_ip": dhcp_range.end_ip,
                            "network_id": dhcp_range.network_id,
                        },
                        "network": {
                            "id": network.id,
                            "network": f"{network.network}/{network.cidr}",
                            "name": network.name,
                            "domain": network.domain,
                            "vlan_id": network.vlan_id,
                            "location": network.location,
                        },
                    }
                return {
                    "ip_address": ip_address,
                    "status": "available",
                    "network": {
                        "id": network.id,
                        "network": f"{network.network}/{network.cidr}",
                        "name": network.name,
                        "domain": network.domain,
                        "vlan_id": network.vlan_id,
                        "location": network.location,
                    },
                }

        # IP not in any managed network
        return {
            "ip_address": ip_address,
            "status": "unmanaged",
            "message": "IP address is not in any managed network",
        }
