"""JSON import functionality."""

import ipaddress
import json
from datetime import datetime
from typing import Any

from ipam.normalize import normalize_network_address

from . import BaseImporter


class JSONImporter(BaseImporter):
    """JSON format importer."""

    @property
    def format_name(self) -> str:
        return "JSON"

    @property
    def file_extensions(self) -> list[str]:
        return ["json"]

    def import_networks(self, file_content: bytes) -> list[dict[str, Any]]:
        """Import networks from JSON content."""
        json_content = file_content.decode("utf-8")
        data = json.loads(json_content)

        # Handle both direct array and our export format
        if isinstance(data, dict) and "data" in data:
            networks_data = data["data"]
        elif isinstance(data, list):
            networks_data = data
        else:
            raise ValueError(
                "Invalid JSON format: expected array or object with 'data' field"
            )

        networks = []
        for network_data in networks_data:
            networks.append(
                {
                    "network": network_data.get("network", "").strip(),
                    "cidr": str(network_data.get("cidr", "")).strip(),
                    **{
                        field: str(network_data.get(column) or "").strip()
                        for field, column in {
                            "name": "name",
                            "domain": "domain",
                            "vlan_id": "vlan_id",
                            "location": "location",
                            "description": "description",
                        }.items()
                        if column in network_data
                    },
                }
            )

        return networks

    def import_hosts(self, file_content: bytes) -> list[dict[str, Any]]:
        """Import hosts from JSON content."""
        json_content = file_content.decode("utf-8")
        data = json.loads(json_content)

        # Handle both direct array and our export format
        if isinstance(data, dict) and "data" in data:
            hosts_data = data["data"]
        elif isinstance(data, list):
            hosts_data = data
        else:
            raise ValueError(
                "Invalid JSON format: expected array or object with 'data' field"
            )

        hosts = []
        for host_data in hosts_data:
            hosts.append(
                {
                    "ip_address": host_data.get("ip_address", "").strip(),
                    **{
                        field: (
                            str(host_data[field] or "").strip()
                            if field not in ("is_assigned", "last_seen")
                            else host_data[field]
                        )
                        for field in (
                            "hostname",
                            "mac_address",
                            "status",
                            "is_assigned",
                            "last_seen",
                            "discovery_source",
                            "description",
                        )
                        if field in host_data
                    },
                }
            )

        return hosts

    def validate_networks_data(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
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

                # Normalize before matching or storing networks.
                network_data["network"] = normalize_network_address(
                    network_data["network"], cidr
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
        self, data: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
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

            supplied_fields = set(host_data)
            try:
                # Validate IP address format
                ipaddress.IPv4Address(host_data["ip_address"])

                # Validate status
                valid_statuses = ["active", "inactive", "reserved"]
                if host_data.get("status") not in valid_statuses:
                    host_data["status"] = "active"

                # Validate and normalize is_assigned
                if host_data.get("is_assigned") not in (None, ""):
                    if isinstance(host_data["is_assigned"], bool):
                        pass
                    elif isinstance(host_data["is_assigned"], str):
                        value = host_data["is_assigned"].strip().lower()
                        if value in ["1", "true", "yes", "on"]:
                            host_data["is_assigned"] = True
                        elif value in ["0", "false", "no", "off"]:
                            host_data["is_assigned"] = False
                        else:
                            errors.append(
                                f"Entry {entry_num}: Invalid is_assigned value"
                            )
                            continue
                    else:
                        errors.append(
                            f"Entry {entry_num}: Invalid is_assigned value"
                        )
                        continue
                else:
                    host_data["is_assigned"] = None

                # Validate last_seen
                if host_data.get("last_seen"):
                    try:
                        normalized = str(host_data["last_seen"]).strip()
                        if normalized.endswith("Z"):
                            normalized = f"{normalized[:-1]}+00:00"
                        host_data["last_seen"] = datetime.fromisoformat(
                            normalized
                        )
                    except ValueError:
                        errors.append(
                            f"Entry {entry_num}: Invalid last_seen timestamp"
                        )
                        continue
                else:
                    host_data["last_seen"] = None

                if not host_data.get("discovery_source"):
                    host_data["discovery_source"] = None

                valid_data.append(
                    {key: host_data[key] for key in supplied_fields}
                )

            except ipaddress.AddressValueError as e:
                errors.append(
                    f"Entry {entry_num}: Invalid IP address - {str(e)}"
                )

        return valid_data, errors
