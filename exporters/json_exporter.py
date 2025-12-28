"""JSON export functionality."""

import json
from typing import Any, List

from . import BaseExporter


class JSONExporter(BaseExporter):
    """JSON format exporter."""

    @property
    def format_name(self) -> str:
        return "JSON"

    @property
    def file_extension(self) -> str:
        return "json"

    @property
    def mime_type(self) -> str:
        return "application/json"

    def export_networks(self, networks: List[Any]) -> bytes:
        """Export networks to JSON format."""
        data = {"export_type": "networks", "export_version": "1.0", "data": []}

        for network in networks:
            data["data"].append(
                {
                    "network": network.network,
                    "cidr": network.cidr,
                    "broadcast_address": network.broadcast_address,
                    "vlan_id": network.vlan_id,
                    "location": network.location,
                    "description": network.description,
                    "statistics": {
                        "total_hosts": network.total_hosts,
                        "used_hosts": network.used_hosts,
                        "available_hosts": network.available_hosts,
                    },
                }
            )

        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    def export_hosts(self, hosts: List[Any]) -> bytes:
        """Export hosts to JSON format."""
        data = {"export_type": "hosts", "export_version": "1.0", "data": []}

        for host in hosts:
            network_info = None
            if host.network_ref:
                network_info = {
                    "network": host.network_ref.network,
                    "cidr": host.network_ref.cidr,
                    "vlan_id": host.network_ref.vlan_id,
                }

            data["data"].append(
                {
                    "ip_address": host.ip_address,
                    "hostname": host.hostname,
                    "mac_address": host.mac_address,
                    "status": host.status,
                    "is_assigned": host.is_assigned,
                    "last_seen": (
                        host.last_seen.isoformat() if host.last_seen else None
                    ),
                    "discovery_source": host.discovery_source,
                    "description": host.description,
                    "network": network_info,
                }
            )

        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
