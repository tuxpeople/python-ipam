"""CSV import functionality."""

import csv
import io
import ipaddress
from datetime import datetime
from typing import Any, Dict, List, Tuple

from . import BaseImporter


class CSVImporter(BaseImporter):
    """CSV format importer."""

    @property
    def format_name(self) -> str:
        return "CSV"

    @property
    def file_extensions(self) -> List[str]:
        return ["csv"]

    def import_networks(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import networks from CSV content."""
        csv_content = file_content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        networks = []
        for row in csv_reader:
            networks.append(
                {
                    "network": row.get("Network", "").strip(),
                    "cidr": row.get("CIDR", "").strip(),
                    "vlan_id": row.get("VLAN ID", "").strip(),
                    "location": row.get("Location", "").strip(),
                    "description": row.get("Description", "").strip(),
                }
            )

        return networks

    def import_hosts(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import hosts from CSV content."""
        csv_content = file_content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        hosts = []
        for row in csv_reader:
            hosts.append(
                {
                    "ip_address": row.get("IP Address", "").strip(),
                    "hostname": row.get("Hostname", "").strip(),
                    "mac_address": row.get("MAC Address", "").strip(),
                    "status": row.get("Status", "active").strip(),
                    "is_assigned": row.get("Is Assigned", "").strip(),
                    "last_seen": row.get("Last Seen", "").strip(),
                    "discovery_source": row.get("Discovery Source", "").strip(),
                    "description": row.get("Description", "").strip(),
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
            row_num = i + 2  # +2 because CSV starts at row 1 and has header

            # Check required fields
            if not network_data.get("network") or not network_data.get("cidr"):
                errors.append(
                    f"Row {row_num}: Missing required fields (Network, CIDR)"
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
                    f"Row {row_num}: Invalid network format - {str(e)}"
                )

        return valid_data, errors

    def validate_hosts_data(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate hosts data."""
        valid_data = []
        errors = []

        for i, host_data in enumerate(data):
            row_num = i + 2  # +2 because CSV starts at row 1 and has header

            # Check required fields
            if not host_data.get("ip_address"):
                errors.append(
                    f"Row {row_num}: Missing required field (IP Address)"
                )
                continue

            try:
                # Validate IP address format
                ipaddress.IPv4Address(host_data["ip_address"])

                # Validate status
                valid_statuses = ["active", "inactive", "reserved"]
                if host_data.get("status") not in valid_statuses:
                    host_data["status"] = "active"

                # Validate and normalize is_assigned
                if host_data.get("is_assigned"):
                    value = host_data["is_assigned"].strip().lower()
                    if value in ["1", "true", "yes", "on"]:
                        host_data["is_assigned"] = True
                    elif value in ["0", "false", "no", "off"]:
                        host_data["is_assigned"] = False
                    else:
                        errors.append(
                            f"Row {row_num}: Invalid Is Assigned value"
                        )
                        continue
                else:
                    host_data["is_assigned"] = None

                # Validate last_seen
                if host_data.get("last_seen"):
                    try:
                        normalized = host_data["last_seen"].strip()
                        if normalized.endswith("Z"):
                            normalized = f"{normalized[:-1]}+00:00"
                        host_data["last_seen"] = datetime.fromisoformat(
                            normalized
                        )
                    except ValueError:
                        errors.append(
                            f"Row {row_num}: Invalid Last Seen timestamp"
                        )
                        continue
                else:
                    host_data["last_seen"] = None

                if not host_data.get("discovery_source"):
                    host_data["discovery_source"] = None

                valid_data.append(host_data)

            except ipaddress.AddressValueError as e:
                errors.append(f"Row {row_num}: Invalid IP address - {str(e)}")

        return valid_data, errors
