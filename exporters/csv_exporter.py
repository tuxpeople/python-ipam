"""CSV export functionality."""

import csv
import io
from typing import Any, List

from . import BaseExporter


class CSVExporter(BaseExporter):
    """CSV format exporter."""

    @property
    def format_name(self) -> str:
        return "CSV"

    @property
    def file_extension(self) -> str:
        return "csv"

    @property
    def mime_type(self) -> str:
        return "text/csv"

    def export_networks(self, networks: List[Any]) -> bytes:
        """Export networks to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Header
        writer.writerow(
            [
                "Network",
                "CIDR",
                "Broadcast Address",
                "VLAN ID",
                "Location",
                "Description",
                "Total Hosts",
                "Used Hosts",
                "Available Hosts",
            ]
        )

        # Data rows
        for network in networks:
            writer.writerow(
                [
                    network.network,
                    network.cidr,
                    network.broadcast_address or "",
                    network.vlan_id or "",
                    network.location or "",
                    network.description or "",
                    network.total_hosts,
                    network.used_hosts,
                    network.available_hosts,
                ]
            )

        return output.getvalue().encode("utf-8")

    def export_hosts(self, hosts: List[Any]) -> bytes:
        """Export hosts to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Header
        writer.writerow(
            [
                "IP Address",
                "Hostname",
                "MAC Address",
                "Status",
                "Is Assigned",
                "Last Seen",
                "Discovery Source",
                "Network",
                "Description",
            ]
        )

        # Data rows
        for host in hosts:
            network_info = ""
            if host.network_ref:
                network_info = (
                    f"{host.network_ref.network}/{host.network_ref.cidr}"
                )

            writer.writerow(
                [
                    host.ip_address,
                    host.hostname or "",
                    host.mac_address or "",
                    host.status,
                    host.is_assigned,
                    host.last_seen.isoformat() if host.last_seen else "",
                    host.discovery_source or "",
                    network_info,
                    host.description or "",
                ]
            )

        return output.getvalue().encode("utf-8")
