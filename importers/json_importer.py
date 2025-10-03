"""JSON import functionality."""

import json
import ipaddress
from typing import Any, Dict, List, Tuple

from . import BaseImporter


class JSONImporter(BaseImporter):
    """JSON format importer."""

    @property
    def format_name(self) -> str:
        return "JSON"

    @property
    def file_extensions(self) -> List[str]:
        return ["json"]

    def import_networks(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import networks from JSON content."""
        json_content = file_content.decode("utf-8")
        data = json.loads(json_content)

        # Handle both direct array and our export format
        if isinstance(data, dict) and "data" in data:
            networks_data = data["data"]
        elif isinstance(data, list):
            networks_data = data
        else:
            raise ValueError("Invalid JSON format: expected array or object with 'data' field")

        networks = []
        for network_data in networks_data:
            networks.append(
                {
                    "network": network_data.get("network", "").strip(),
                    "cidr": str(network_data.get("cidr", "")).strip(),
                    "vlan_id": str(network_data.get("vlan_id", "")).strip(),
                    "location": network_data.get("location", "").strip(),
                    "description": network_data.get("description", "").strip(),
                }
            )

        return networks

    def import_hosts(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import hosts from JSON content."""
        json_content = file_content.decode("utf-8")
        data = json.loads(json_content)

        # Handle both direct array and our export format
        if isinstance(data, dict) and "data" in data:
            hosts_data = data["data"]
        elif isinstance(data, list):
            hosts_data = data
        else:
            raise ValueError("Invalid JSON format: expected array or object with 'data' field")

        hosts = []
        for host_data in hosts_data:
            hosts.append(
                {
                    "ip_address": host_data.get("ip_address", "").strip(),
                    "hostname": host_data.get("hostname", "").strip(),
                    "mac_address": host_data.get("mac_address", "").strip(),
                    "status": host_data.get("status", "active").strip(),
                    "description": host_data.get("description", "").strip(),
                }
            )

        return hosts

    def validate_networks_data(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate networks data."""
        valid_data = []
        errors = []

        for i, network_data in enumerate(data):
            entry_num = i + 1

            # Check required fields
            if not network_data.get("network") or not network_data.get("cidr"):
                errors.append(
                    f"Entry {entry_num}: Missing required fields (network, cidr)"
                )
                continue

            try:
                # Validate network format
                cidr = int(network_data["cidr"])
                network_obj = ipaddress.IPv4Network(
                    f"{network_data['network']}/{cidr}", strict=False
                )

                # Add computed fields
                network_data["cidr"] = cidr
                network_data["broadcast_address"] = str(
                    network_obj.broadcast_address
                )

                # Validate VLAN ID if provided
                if network_data.get("vlan_id"):
                    try:
                        network_data["vlan_id"] = int(network_data["vlan_id"])
                    except ValueError:
                        network_data["vlan_id"] = None

                valid_data.append(network_data)

            except (ValueError, ipaddress.AddressValueError) as e:
                errors.append(
                    f"Entry {entry_num}: Invalid network format - {str(e)}"
                )

        return valid_data, errors

    def validate_hosts_data(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate hosts data."""
        valid_data = []
        errors = []

        for i, host_data in enumerate(data):
            entry_num = i + 1

            # Check required fields
            if not host_data.get("ip_address"):
                errors.append(
                    f"Entry {entry_num}: Missing required field (ip_address)"
                )
                continue

            try:
                # Validate IP address format
                ipaddress.IPv4Address(host_data["ip_address"])

                # Validate status
                valid_statuses = ["active", "inactive", "reserved"]
                if host_data.get("status") not in valid_statuses:
                    host_data["status"] = "active"

                valid_data.append(host_data)

            except ipaddress.AddressValueError as e:
                errors.append(f"Entry {entry_num}: Invalid IP address - {str(e)}")

        return valid_data, errors