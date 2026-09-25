"""Test export and import functionality."""

import csv
import json
from datetime import datetime
from io import BytesIO, StringIO

import pytest

from exporters.csv_exporter import CSVExporter
from exporters.dnsmasq_exporter import DNSmasqExporter
from exporters.json_exporter import JSONExporter
from importers.csv_importer import CSVImporter
from importers.json_importer import JSONImporter
from ipam.extensions import db
from ipam.models import Host, Network


class TestExporters:
    def test_csv_exporter_networks(self, app_context):
        """Test CSV export for networks."""
        # Create test networks
        network1 = Network(
            network="192.168.10.0",
            cidr=24,
            broadcast_address="192.168.10.255",
            vlan_id=100,
            description="Test network 1",
            location="Office",
        )
        network2 = Network(
            network="10.10.0.0", cidr=16, broadcast_address="10.10.255.255"
        )
        db.session.add(network1)
        db.session.add(network2)
        db.session.commit()

        # Export networks
        exporter = CSVExporter()
        exported_data = exporter.export_networks([network1, network2])

        # Verify export
        assert isinstance(exported_data, bytes)
        csv_content = exported_data.decode("utf-8")
        assert "Network,CIDR,Broadcast Address" in csv_content
        assert "192.168.10.0,24,192.168.10.255" in csv_content
        assert "10.10.0.0,16,10.10.255.255" in csv_content

    def test_csv_exporter_hosts(self, app_context):
        """Test CSV export for hosts."""
        # Create test data
        network = Network(network="192.168.1.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        host1 = Host(
            ip_address="192.168.1.10",
            hostname="server01",
            mac_address="aa:bb:cc:dd:ee:ff",
            status="active",
            network_id=network.id,
        )
        host2 = Host(ip_address="192.168.1.11", status="inactive")
        db.session.add(host1)
        db.session.add(host2)
        db.session.commit()

        # Export hosts
        exporter = CSVExporter()
        exported_data = exporter.export_hosts([host1, host2])

        # Verify export
        csv_content = exported_data.decode("utf-8")
        assert "IP Address,Hostname,MAC Address" in csv_content
        assert "192.168.1.10,server01,aa:bb:cc:dd:ee:ff" in csv_content
        assert "192.168.1.11,," in csv_content

    def test_json_exporter_networks(self, app_context):
        """Test JSON export for networks."""
        network = Network(
            network="192.168.1.0",
            cidr=24,
            broadcast_address="192.168.1.255",
            vlan_id=100,
        )
        db.session.add(network)
        db.session.commit()

        # Export networks
        exporter = JSONExporter()
        exported_data = exporter.export_networks([network])

        # Verify export
        json_data = json.loads(exported_data.decode("utf-8"))
        assert json_data["export_type"] == "networks"
        assert json_data["export_version"] == "1.0"
        assert len(json_data["data"]) == 1
        assert json_data["data"][0]["network"] == "192.168.1.0"
        assert json_data["data"][0]["cidr"] == 24

    def test_json_exporter_hosts(self, app_context):
        """Test JSON export for hosts."""
        host = Host(ip_address="192.168.1.10", hostname="server01")
        db.session.add(host)
        db.session.commit()

        # Export hosts
        exporter = JSONExporter()
        exported_data = exporter.export_hosts([host])

        # Verify export
        json_data = json.loads(exported_data.decode("utf-8"))
        assert json_data["export_type"] == "hosts"
        assert len(json_data["data"]) == 1
        assert json_data["data"][0]["ip_address"] == "192.168.1.10"

    def test_dnsmasq_exporter_hosts(self, app_context):
        """Test DNSmasq export for hosts."""
        # Create test hosts with different scenarios
        host1 = Host(
            ip_address="192.168.14.10",
            hostname="server01",
            mac_address="aa:bb:cc:dd:ee:ff",
            status="active",
            description="Active host with MAC",
        )
        host2 = Host(
            ip_address="192.168.14.11",
            hostname="server02",
            status="active",
            description="Active host without MAC",
        )
        host3 = Host(
            ip_address="192.168.14.12",
            hostname="reserved-host",
            mac_address="bb:cc:dd:ee:ff:aa",
            status="reserved",
            description="Reserved host",
        )
        host4 = Host(
            ip_address="192.168.14.13",
            status="inactive",
            description="Inactive host - should be skipped",
        )
        host5 = Host(
            ip_address="192.168.14.14",
            mac_address="cc:dd:ee:ff:aa:bb",
            status="active",
            description="Host without hostname - should be skipped",
        )

        db.session.add_all([host1, host2, host3, host4, host5])
        db.session.commit()

        # Export hosts
        exporter = DNSmasqExporter()
        exported_data = exporter.export_hosts(
            [host1, host2, host3, host4, host5]
        )

        # Verify export
        dnsmasq_content = exported_data.decode("utf-8")

        # Check header comments
        assert "# DNSmasq host configuration" in dnsmasq_content
        assert "# Generated by Python IPAM" in dnsmasq_content

        # Check active hosts section
        assert "# Active hosts" in dnsmasq_content
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:ff,192.168.14.10,server01"
            in dnsmasq_content
        )
        assert "host-record=server02,192.168.14.11" in dnsmasq_content

        # Check reserved hosts section
        assert "# Reserved hosts" in dnsmasq_content
        assert (
            "dhcp-host=bb:cc:dd:ee:ff:aa,192.168.14.12,reserved-host"
            in dnsmasq_content
        )

        # Check statistics
        assert "# Total exported entries: 3" in dnsmasq_content
        assert "# DHCP reservations: 2" in dnsmasq_content
        assert "# DNS records: 1" in dnsmasq_content

        # Verify inactive and hostname-less hosts are not included
        assert "192.168.14.13" not in dnsmasq_content
        assert "192.168.14.14" not in dnsmasq_content

    def test_dnsmasq_exporter_networks_not_supported(self, app_context):
        """Test that DNSmasq exporter doesn't support network export."""
        network = Network(network="192.168.15.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        exporter = DNSmasqExporter()

        with pytest.raises(NotImplementedError) as exc_info:
            exporter.export_networks([network])

        assert "only supports host exports" in str(exc_info.value)

    def test_dnsmasq_exporter_dns_mode(self, app_context):
        """Test DNSmasq export in DNS-only mode."""
        # Create test hosts
        host1 = Host(
            ip_address="192.168.17.10",
            hostname="dns-host1",
            mac_address="aa:bb:cc:dd:ee:ff",
            status="active",
        )
        host2 = Host(
            ip_address="192.168.17.11",
            hostname="dns-host2",
            status="active",
        )

        db.session.add_all([host1, host2])
        db.session.commit()

        # Export in DNS mode
        exporter = DNSmasqExporter("dns")
        exported_data = exporter.export_hosts([host1, host2])
        dnsmasq_content = exported_data.decode("utf-8")

        # Check DNS mode header
        assert "# DNSmasq host configuration - DNS mode" in dnsmasq_content
        assert "# DNS-only mode: host-record=hostname,IP" in dnsmasq_content

        # Both hosts should have host-record entries (ignore MAC addresses)
        assert "host-record=dns-host1,192.168.17.10" in dnsmasq_content
        assert "host-record=dns-host2,192.168.17.11" in dnsmasq_content

        # No dhcp-host entries should be present
        assert "dhcp-host=" not in dnsmasq_content

        # Check statistics
        assert "# DNS records: 2" in dnsmasq_content

    def test_dnsmasq_exporter_dhcp_mode(self, app_context):
        """Test DNSmasq export in DHCP-only mode."""
        # Create test hosts
        host1 = Host(
            ip_address="192.168.18.10",
            hostname="dhcp-host1",
            mac_address="aa:bb:cc:dd:ee:01",
            status="active",
        )
        host2 = Host(
            ip_address="192.168.18.11",
            hostname="dhcp-host2",
            status="active",
            # No MAC address - should be skipped in DHCP mode
        )

        db.session.add_all([host1, host2])
        db.session.commit()

        # Export in DHCP mode
        exporter = DNSmasqExporter("dhcp")
        exported_data = exporter.export_hosts([host1, host2])
        dnsmasq_content = exported_data.decode("utf-8")

        # Check DHCP mode header
        assert "# DNSmasq host configuration - DHCP mode" in dnsmasq_content
        assert "# DHCP-only mode: dhcp-host=MAC,IP,hostname" in dnsmasq_content

        # Only host with MAC should have dhcp-host entry
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:01,192.168.18.10,dhcp-host1"
            in dnsmasq_content
        )

        # No host-record entries should be present
        assert "host-record=" not in dnsmasq_content

        # Host without MAC should not appear
        assert "dhcp-host2" not in dnsmasq_content

        # Check statistics
        assert "# DHCP reservations: 1" in dnsmasq_content

    def test_dnsmasq_exporter_combined_mode(self, app_context):
        """Test DNSmasq export in combined mode."""
        # Create test hosts
        host1 = Host(
            ip_address="192.168.19.10",
            hostname="combined-host1",
            mac_address="aa:bb:cc:dd:ee:01",
            status="active",
        )
        host2 = Host(
            ip_address="192.168.19.11",
            hostname="combined-host2",
            status="active",
            # No MAC address - should get host-record
        )

        db.session.add_all([host1, host2])
        db.session.commit()

        # Export in combined mode (default)
        exporter = DNSmasqExporter("combined")
        exported_data = exporter.export_hosts([host1, host2])
        dnsmasq_content = exported_data.decode("utf-8")

        # Check combined mode header
        assert "# DNSmasq host configuration - COMBINED mode" in dnsmasq_content
        assert (
            "# Combined mode: dhcp-host=MAC,IP,hostname + host-record=hostname,IP"
            in dnsmasq_content
        )

        # Host with MAC should have dhcp-host entry
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:01,192.168.19.10,combined-host1"
            in dnsmasq_content
        )

        # Host without MAC should have host-record entry
        assert "host-record=combined-host2,192.168.19.11" in dnsmasq_content

        # Check statistics
        assert "# DHCP reservations: 1" in dnsmasq_content
        assert "# DNS records: 1" in dnsmasq_content


class TestImporters:
    def test_csv_importer_networks(self):
        """Test CSV import for networks."""
        csv_content = b"""Network,CIDR,VLAN ID,Location,Description
192.168.1.0,24,100,Office,Test network
10.0.0.0,16,,Datacenter,Production network"""

        importer = CSVImporter()
        networks_data = importer.import_networks(csv_content)

        assert len(networks_data) == 2
        assert networks_data[0]["network"] == "192.168.1.0"
        assert networks_data[0]["cidr"] == "24"
        assert networks_data[0]["vlan_id"] == "100"
        assert networks_data[1]["network"] == "10.0.0.0"

    def test_csv_importer_hosts(self):
        """Test CSV import for hosts."""
        csv_content = b"""IP Address,Hostname,MAC Address,Status,Description
192.168.1.10,server01,aa:bb:cc:dd:ee:ff,active,Web server
192.168.1.11,server02,,inactive,Database server"""

        importer = CSVImporter()
        hosts_data = importer.import_hosts(csv_content)

        assert len(hosts_data) == 2
        assert hosts_data[0]["ip_address"] == "192.168.1.10"
        assert hosts_data[0]["hostname"] == "server01"
        assert hosts_data[1]["status"] == "inactive"

    def test_csv_importer_validate_networks(self):
        """Test network data validation."""
        networks_data = [
            {
                "network": "192.168.1.0",
                "cidr": "24",
                "vlan_id": "100",
                "location": "Office",
                "description": "Valid network",
            },
            {
                "network": "invalid",
                "cidr": "24",
                "vlan_id": "",
                "location": "",
                "description": "",
            },
            {
                "network": "",
                "cidr": "",
                "vlan_id": "",
                "location": "",
                "description": "",
            },
        ]

        importer = CSVImporter()
        valid_data, errors = importer.validate_networks_data(networks_data)

        assert len(valid_data) == 1
        assert len(errors) == 2
        assert valid_data[0]["network"] == "192.168.1.0"
        assert valid_data[0]["cidr"] == 24
        assert valid_data[0]["vlan_id"] == 100

    def test_csv_importer_validate_hosts(self):
        """Test host data validation."""
        hosts_data = [
            {
                "ip_address": "192.168.1.10",
                "hostname": "server01",
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "status": "active",
                "description": "Valid host",
            },
            {
                "ip_address": "invalid.ip",
                "hostname": "server02",
                "mac_address": "",
                "status": "active",
                "description": "",
            },
            {
                "ip_address": "",
                "hostname": "",
                "mac_address": "",
                "status": "",
                "description": "",
            },
        ]

        importer = CSVImporter()
        valid_data, errors = importer.validate_hosts_data(hosts_data)

        assert len(valid_data) == 1
        assert len(errors) == 2
        assert valid_data[0]["ip_address"] == "192.168.1.10"

    def test_json_importer_networks(self):
        """Test JSON import for networks."""
        json_content = json.dumps(
            [
                {
                    "network": "192.168.1.0",
                    "cidr": 24,
                    "vlan_id": 100,
                    "location": "Office",
                    "description": "Test network",
                },
                {
                    "network": "10.0.0.0",
                    "cidr": 16,
                    "location": "Datacenter",
                    "description": "Production network",
                },
            ]
        ).encode("utf-8")

        importer = JSONImporter()
        networks_data = importer.import_networks(json_content)

        assert len(networks_data) == 2
        assert networks_data[0]["network"] == "192.168.1.0"
        assert networks_data[0]["cidr"] == "24"
        assert networks_data[0]["vlan_id"] == "100"
        assert networks_data[1]["network"] == "10.0.0.0"

    def test_json_importer_hosts(self):
        """Test JSON import for hosts."""
        json_content = json.dumps(
            [
                {
                    "ip_address": "192.168.1.10",
                    "hostname": "server01",
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "status": "active",
                    "description": "Web server",
                },
                {
                    "ip_address": "192.168.1.11",
                    "hostname": "server02",
                    "status": "inactive",
                    "description": "Database server",
                },
            ]
        ).encode("utf-8")

        importer = JSONImporter()
        hosts_data = importer.import_hosts(json_content)

        assert len(hosts_data) == 2
        assert hosts_data[0]["ip_address"] == "192.168.1.10"
        assert hosts_data[0]["hostname"] == "server01"
        assert hosts_data[1]["status"] == "inactive"

    def test_json_importer_export_format(self):
        """Test JSON import from our export format."""
        json_content = json.dumps(
            {
                "export_type": "networks",
                "export_version": "1.0",
                "data": [
                    {
                        "network": "192.168.1.0",
                        "cidr": 24,
                        "vlan_id": 100,
                        "location": "Office",
                        "description": "Test network",
                    }
                ],
            }
        ).encode("utf-8")

        importer = JSONImporter()
        networks_data = importer.import_networks(json_content)

        assert len(networks_data) == 1
        assert networks_data[0]["network"] == "192.168.1.0"
        assert networks_data[0]["cidr"] == "24"

    def test_json_importer_validate_networks(self):
        """Test JSON network data validation."""
        networks_data = [
            {
                "network": "192.168.1.0",
                "cidr": "24",
                "vlan_id": "100",
                "location": "Office",
                "description": "Valid network",
            },
            {
                "network": "invalid",
                "cidr": "24",
                "vlan_id": "",
                "location": "",
                "description": "",
            },
            {
                "network": "",
                "cidr": "",
                "vlan_id": "",
                "location": "",
                "description": "",
            },
        ]

        importer = JSONImporter()
        valid_data, errors = importer.validate_networks_data(networks_data)

        assert len(valid_data) == 1
        assert len(errors) == 2
        assert valid_data[0]["network"] == "192.168.1.0"
        assert valid_data[0]["cidr"] == 24
        assert valid_data[0]["vlan_id"] == 100

    def test_json_importer_validate_hosts(self):
        """Test JSON host data validation."""
        hosts_data = [
            {
                "ip_address": "192.168.1.10",
                "hostname": "server01",
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "status": "active",
                "description": "Valid host",
            },
            {
                "ip_address": "invalid.ip",
                "hostname": "server02",
                "mac_address": "",
                "status": "active",
                "description": "",
            },
            {
                "ip_address": "",
                "hostname": "",
                "mac_address": "",
                "status": "",
                "description": "",
            },
        ]

        importer = JSONImporter()
        valid_data, errors = importer.validate_hosts_data(hosts_data)

        assert len(valid_data) == 1
        assert len(errors) == 2
        assert valid_data[0]["ip_address"] == "192.168.1.10"


class TestExportRoutes:
    def test_export_networks_csv(self, client):
        """Test network CSV export route."""
        with client.application.app_context():
            network = Network(network="192.168.1.0", cidr=24)
            db.session.add(network)
            db.session.commit()

        response = client.get("/export/networks/csv")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert (
            "attachment; filename=networks.csv"
            in response.headers["Content-Disposition"]
        )
        assert b"192.168.1.0" in response.data

    def test_export_hosts_json(self, client):
        """Test host JSON export route."""
        with client.application.app_context():
            host = Host(ip_address="192.168.1.10", hostname="server01")
            db.session.add(host)
            db.session.commit()

        response = client.get("/export/hosts/json")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert (
            "attachment; filename=hosts.json"
            in response.headers["Content-Disposition"]
        )

        json_data = json.loads(response.data)
        assert json_data["export_type"] == "hosts"
        assert len(json_data["data"]) == 1

    def test_export_invalid_format(self, client):
        """Test export with invalid format."""
        response = client.get(
            "/export/networks/invalid_format", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Export failed" in response.data

    def test_legacy_export_routes(self, client):
        """Test legacy export routes redirect correctly."""
        response = client.get("/export/networks", follow_redirects=False)
        assert response.status_code == 302
        assert "/export/networks/csv" in response.location

        response = client.get("/export/hosts", follow_redirects=False)
        assert response.status_code == 302
        assert "/export/hosts/csv" in response.location

    def test_export_hosts_dnsmasq(self, client):
        """Test host DNSmasq export route."""
        with client.application.app_context():
            host = Host(
                ip_address="192.168.16.10",
                hostname="testhost",
                mac_address="aa:bb:cc:dd:ee:ff",
                status="active",
            )
            db.session.add(host)
            db.session.commit()

        response = client.get("/export/hosts/dnsmasq")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        assert (
            "attachment; filename=hosts.conf"
            in response.headers["Content-Disposition"]
        )

        # Check DNSmasq format
        dnsmasq_content = response.data.decode("utf-8")
        assert "# DNSmasq host configuration" in dnsmasq_content
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:ff,192.168.16.10,testhost"
            in dnsmasq_content
        )

    def test_export_hosts_dnsmasq_modes(self, client):
        """Test DNSmasq export routes for different modes."""
        with client.application.app_context():
            host1 = Host(
                ip_address="192.168.20.10",
                hostname="mode-test1",
                mac_address="aa:bb:cc:dd:ee:01",
                status="active",
            )
            host2 = Host(
                ip_address="192.168.20.11",
                hostname="mode-test2",
                status="active",
                # No MAC address
            )
            db.session.add_all([host1, host2])
            db.session.commit()

        # Test DNS-only mode
        response = client.get("/export/hosts/dnsmasq-dns")
        assert response.status_code == 200
        dns_content = response.data.decode("utf-8")
        assert "# DNSmasq host configuration - DNS mode" in dns_content
        assert "host-record=mode-test1,192.168.20.10" in dns_content
        assert "host-record=mode-test2,192.168.20.11" in dns_content
        assert "dhcp-host=" not in dns_content

        # Test DHCP-only mode
        response = client.get("/export/hosts/dnsmasq-dhcp")
        assert response.status_code == 200
        dhcp_content = response.data.decode("utf-8")
        assert "# DNSmasq host configuration - DHCP mode" in dhcp_content
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:01,192.168.20.10,mode-test1"
            in dhcp_content
        )
        assert (
            "mode-test2" not in dhcp_content
        )  # No MAC, so skipped in DHCP mode
        assert "host-record=" not in dhcp_content

        # Test combined mode (default)
        response = client.get("/export/hosts/dnsmasq")
        assert response.status_code == 200
        combined_content = response.data.decode("utf-8")
        assert (
            "# DNSmasq host configuration - COMBINED mode" in combined_content
        )
        assert (
            "dhcp-host=aa:bb:cc:dd:ee:01,192.168.20.10,mode-test1"
            in combined_content
        )
        assert "host-record=mode-test2,192.168.20.11" in combined_content


class TestImportRoutes:
    def test_import_page_loads(self, client):
        """Test import page loads with form."""
        response = client.get("/import")
        assert response.status_code == 200
        assert b"Import Data" in response.data
        assert b"CSV" in response.data

    def test_import_networks_csv(self, client):
        """Test importing networks via CSV upload."""
        csv_data = b"""Network,CIDR,VLAN ID,Location,Description
192.168.1.0,24,100,Office,Test network"""

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "networks.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 networks!" in response.data

        # Verify network was created
        with client.application.app_context():
            network = Network.query.filter_by(network="192.168.1.0").first()
            assert network is not None
            assert network.cidr == 24
            assert network.vlan_id == 100

    @pytest.mark.parametrize("format_name", ["csv", "json"])
    @pytest.mark.parametrize(
        "fields, expected",
        [
            ({}, (None, None)),
            ({"name": "", "domain": ""}, (None, None)),
            ({"name": None, "domain": None}, (None, None)),
            ({"name": " Office LAN "}, ("Office LAN", None)),
            ({"domain": " example.com "}, (None, "example.com")),
            (
                {"name": " Office LAN ", "domain": " example.com "},
                ("Office LAN", "example.com"),
            ),
        ],
    )
    def test_import_network_optional_metadata(
        self, client, format_name, fields, expected
    ):
        """Persist optional network metadata and accept older input files."""
        if format_name == "json":
            content = json.dumps(
                [{"network": "10.42.0.0", "cidr": 24, **fields}]
            ).encode("utf-8")
        else:
            headers = ["Network", "CIDR"] + [key.title() for key in fields]
            values = ["10.42.0.0", "24"] + [
                value or "" for value in fields.values()
            ]
            content = (",".join(headers) + "\n" + ",".join(values)).encode(
                "utf-8"
            )

        response = client.post(
            "/import",
            data={
                "import_type": "networks",
                "format_type": format_name,
                "file": (BytesIO(content), f"networks.{format_name}"),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Successfully imported 1 networks!" in response.data
        with client.application.app_context():
            network = Network.query.filter_by(network="10.42.0.0").one()
            assert (network.name, network.domain) == expected

    @pytest.mark.parametrize("format_name", ["csv", "json"])
    @pytest.mark.parametrize("enabled", [False, True])
    @pytest.mark.parametrize("cidr", [24, 25])
    @pytest.mark.parametrize("address", ["10.42.0.0", "10.42.0.42"])
    def test_update_existing_networks(
        self, client, format_name, enabled, cidr, address
    ):
        """Update supplied fields only, preserving identity and CIDR."""
        with client.application.app_context():
            network = Network(
                network="10.42.0.0",
                cidr=24,
                name="Old name",
                domain="old.example.com",
                location="Office",
                vlan_id=100,
                description="Keep this",
            )
            db.session.add(network)
            db.session.flush()
            network_id = network.id
            db.session.add(
                Host(ip_address="10.42.0.200", network_id=network_id)
            )
            db.session.commit()
        if format_name == "csv":
            content = (
                "Network,CIDR,Name,Domain,VLAN ID\n"
                f"{address},{cidr},New name,,\n"
                "10.43.0.42,24,New network,,"
            ).encode()
        else:
            content = json.dumps(
                [
                    {
                        "network": address,
                        "cidr": cidr,
                        "name": "New name",
                        "domain": None,
                        "vlan_id": None,
                    },
                    {
                        "network": "10.43.0.42",
                        "cidr": 24,
                        "name": "New network",
                    },
                ]
            ).encode()
        data = {
            "import_type": "networks",
            "format_type": format_name,
            "file": (BytesIO(content), f"networks.{format_name}"),
        }
        if enabled:
            data["update_existing"] = "y"
        response = client.post("/import", data=data, follow_redirects=True)
        changed = enabled and cidr == 24
        assert response.status_code == 200
        counts = (
            f"Created: 1, updated: {int(changed)}, skipped: {int(not changed)}."
        )
        assert counts.encode() in response.data
        if enabled and cidr != 24:
            assert b"CIDR changes" in response.data
        with client.application.app_context():
            network = db.session.get(Network, network_id)
            assert Network.query.count() == 2
            assert network.network == "10.42.0.0"
            assert network.cidr == 24
            assert network.name == ("New name" if changed else "Old name")
            assert network.domain == (None if changed else "old.example.com")
            assert network.vlan_id == (None if changed else 100)
            assert network.location == "Office"
            assert network.description == "Keep this"
            assert network.hosts[0].ip_address == "10.42.0.200"
            created = Network.query.filter_by(network="10.43.0.0").one()
            assert created.name == "New network"
            assert created.broadcast_address == "10.43.0.255"

    @pytest.mark.parametrize("format_name", ["csv", "json"])
    @pytest.mark.parametrize("enabled", [False, True])
    @pytest.mark.parametrize("mode", ["partial", "clear", "false", "invalid"])
    def test_update_existing_hosts(self, client, format_name, enabled, mode):
        """Update supplied host fields without losing identity or metadata."""
        seen = datetime(2026, 9, 1, 12, 30)
        with client.application.app_context():
            network = Network(network="10.42.0.0", cidr=24)
            db.session.add(network)
            db.session.flush()
            network_id = network.id
            host = Host(
                ip_address="10.42.0.10",
                hostname="old",
                cname="alias",
                mac_address="aa:bb:cc:dd:ee:ff",
                status="reserved",
                description="Keep this",
                is_assigned=True,
                last_seen=seen,
                discovery_source="manual",
                network_id=network_id,
            )
            db.session.add(host)
            db.session.commit()
            host_id = host.id
        row = {"ip_address": "10.42.0.10", "hostname": " new "}
        if mode == "clear":
            row.update(
                {
                    key: None
                    for key in (
                        "mac_address",
                        "status",
                        "description",
                        "is_assigned",
                        "last_seen",
                        "discovery_source",
                    )
                }
            )
        elif mode == "false":
            row["is_assigned"] = False
        elif mode == "invalid":
            row["last_seen"] = "not-a-timestamp"
        rows = [row, {"ip_address": "10.42.0.11", "hostname": "created"}]
        if format_name == "json":
            content = json.dumps({"data": rows}).encode()
        else:
            columns = {
                "ip_address": "IP Address",
                "hostname": "Hostname",
                "mac_address": "MAC Address",
                "status": "Status",
                "description": "Description",
                "is_assigned": "Is Assigned",
                "last_seen": "Last Seen",
                "discovery_source": "Discovery Source",
            }
            output = StringIO()
            writer = csv.DictWriter(
                output, fieldnames=[columns[k] for k in row]
            )
            writer.writeheader()
            writer.writerows(
                {columns[k]: v for k, v in item.items()} for item in rows
            )
            content = output.getvalue().encode()
        data = {
            "import_type": "hosts",
            "format_type": format_name,
            "file": (BytesIO(content), f"hosts.{format_name}"),
        }
        if enabled:
            data["update_existing"] = "y"
        response = client.post("/import", data=data, follow_redirects=True)
        changed = enabled and mode != "invalid"
        assert response.status_code == 200
        counts = (
            f"Created: 1, updated: {int(changed)}, skipped: {int(not changed)}."
        )
        assert counts.encode() in response.data
        with client.application.app_context():
            host = db.session.get(Host, host_id)
            assert Host.query.count() == 2
            assert host.network_id == network_id
            assert host.cname == "alias"
            assert host.hostname == ("new" if changed else "old")
            cleared = changed and mode == "clear"
            assert host.status == ("active" if cleared else "reserved")
            assert host.description == (None if cleared else "Keep this")
            assert host.mac_address == (
                None if cleared else "aa:bb:cc:dd:ee:ff"
            )
            assert host.last_seen == (None if cleared else seen)
            assert host.discovery_source == (None if cleared else "manual")
            assert host.is_assigned is (
                not (changed and mode in ("clear", "false"))
            )
            created = Host.query.filter_by(ip_address="10.42.0.11").one()
            assert created.status == "active"
            assert created.is_assigned is True
            assert created.network_id == network_id

    def test_import_hosts_csv(self, client):
        """Test importing hosts via CSV upload."""
        csv_data = b"""IP Address,Hostname,MAC Address,Status,Description
192.168.1.10,server01,aa:bb:cc:dd:ee:ff,active,Web server"""

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "hosts.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 hosts!" in response.data

        # Verify host was created
        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host is not None
            assert host.hostname == "server01"

    def test_import_networks_json(self, client):
        """Test importing networks via JSON upload."""
        json_data = json.dumps(
            [
                {
                    "network": "192.168.1.0",
                    "cidr": 24,
                    "vlan_id": 100,
                    "location": "Office",
                    "description": "Test network",
                }
            ]
        ).encode("utf-8")

        data = {
            "import_type": "networks",
            "format_type": "json",
            "file": (BytesIO(json_data), "networks.json"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 networks!" in response.data

        # Verify network was created
        with client.application.app_context():
            network = Network.query.filter_by(network="192.168.1.0").first()
            assert network is not None
            assert network.cidr == 24
            assert network.vlan_id == 100

    def test_import_hosts_json(self, client):
        """Test importing hosts via JSON upload."""
        json_data = json.dumps(
            [
                {
                    "ip_address": "192.168.1.10",
                    "hostname": "server01",
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "status": "active",
                    "description": "Web server",
                }
            ]
        ).encode("utf-8")

        data = {
            "import_type": "hosts",
            "format_type": "json",
            "file": (BytesIO(json_data), "hosts.json"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 hosts!" in response.data

        # Verify host was created
        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host is not None
            assert host.hostname == "server01"

    def test_import_json_export_format(self, client):
        """Test importing from our JSON export format."""
        json_data = json.dumps(
            {
                "export_type": "networks",
                "export_version": "1.0",
                "data": [
                    {
                        "network": "192.168.1.0",
                        "cidr": 24,
                        "vlan_id": 100,
                        "location": "Office",
                        "description": "Exported network",
                    }
                ],
            }
        ).encode("utf-8")

        data = {
            "import_type": "networks",
            "format_type": "json",
            "file": (BytesIO(json_data), "export.json"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 networks!" in response.data

    def test_import_with_errors(self, client):
        """Test import with validation errors."""
        csv_data = b"""IP Address,Hostname,MAC Address,Status,Description
invalid.ip,server01,,active,Invalid IP
192.168.1.10,server02,,active,Valid IP"""

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "hosts.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Import completed with 1 errors" in response.data
        assert b"Successfully imported 1 hosts!" in response.data

    def test_legacy_import_route(self, client):
        """Test legacy import route redirects correctly."""
        response = client.get("/import_csv", follow_redirects=False)
        assert response.status_code == 302
        assert "/import" in response.location


class TestEdgeCases:
    """Test edge cases and error handling scenarios."""

    def test_empty_file_import(self, client):
        """Test importing an empty file."""
        csv_data = b""

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "empty.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        # Empty file import is treated as successful (no data to import)
        assert b"Networks" in response.data

    def test_invalid_csv_format(self, client):
        """Test importing malformed CSV data."""
        csv_data = b"""Network,CIDR,VLAN ID
192.168.1.0,24,100
"Malformed row with quotes and extra commas,,,"""

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "malformed.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200

    def test_duplicate_network_import(self, client):
        """Test importing duplicate networks."""
        with client.application.app_context():
            existing_network = Network(network="192.168.1.0", cidr=24)
            db.session.add(existing_network)
            db.session.commit()

        csv_data = b"""Network,CIDR,VLAN ID,Location,Description
192.168.1.0,24,100,Office,Duplicate network
192.168.2.0,24,200,Office,New network"""

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "duplicates.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 networks!" in response.data

    def test_duplicate_host_import(self, client):
        """Test importing duplicate hosts."""
        with client.application.app_context():
            existing_host = Host(ip_address="192.168.1.10", hostname="existing")
            db.session.add(existing_host)
            db.session.commit()

        csv_data = b"""IP Address,Hostname,MAC Address,Status,Description
192.168.1.10,server01,aa:bb:cc:dd:ee:ff,active,Duplicate host
192.168.1.11,server02,bb:cc:dd:ee:ff:aa,active,New host"""

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "duplicates.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 1 hosts!" in response.data

    def test_utf8_encoding_import(self, client):
        """Test importing data with UTF-8 special characters."""
        csv_data = """Network,CIDR,VLAN ID,Location,Description
192.168.1.0,24,100,München,Netzwerk für Büro
10.0.0.0,16,200,São Paulo,Rede do escritório""".encode()

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "utf8.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 2 networks!" in response.data

        with client.application.app_context():
            network = Network.query.filter_by(location="München").first()
            assert network is not None
            assert "Netzwerk" in network.description

    def test_large_cidr_values(self, client):
        """Test importing networks with edge case CIDR values."""
        csv_data = b"""Network,CIDR,VLAN ID,Location,Description
10.0.0.0,8,100,Office,Large network
192.168.1.0,32,200,Office,Single host network
192.168.2.0,31,300,Office,Point-to-point network"""

        data = {
            "import_type": "networks",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "edge_cidrs.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 3 networks!" in response.data

    def test_invalid_mac_address_format(self, client):
        """Test importing hosts with various MAC address formats."""
        csv_data = b"""IP Address,Hostname,MAC Address,Status,Description
192.168.1.10,server01,aa:bb:cc:dd:ee:ff,active,Valid MAC
192.168.1.11,server02,AA-BB-CC-DD-EE-FF,active,Valid MAC dash format
192.168.1.12,server03,invalid-mac,active,Invalid MAC
192.168.1.13,server04,,active,Empty MAC"""

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "mac_formats.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 4 hosts!" in response.data

    def test_invalid_status_values(self, client):
        """Test importing hosts with invalid status values."""
        csv_data = b"""IP Address,Hostname,MAC Address,Status,Description
192.168.1.10,server01,,unknown,Invalid status
192.168.1.11,server02,,ACTIVE,Invalid case status"""

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "invalid_status.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 2 hosts!" in response.data

        # Verify status was normalized to 'active'
        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host.status == "active"


class TestPerformance:
    """Performance tests for large datasets."""

    def test_large_network_export(self, app_context):
        """Test exporting a large number of networks."""
        # Create 100 networks
        networks = []
        for i in range(100):
            network = Network(
                network=f"10.{i}.0.0",
                cidr=16,
                broadcast_address=f"10.{i}.255.255",
                vlan_id=i + 100,
                location=f"Location {i}",
                description=f"Test network {i}",
            )
            networks.append(network)
            db.session.add(network)
        db.session.commit()

        # Test CSV export performance
        exporter = CSVExporter()
        exported_data = exporter.export_networks(networks)
        assert len(exported_data) > 1000  # Should be substantial data
        assert exported_data.count(b"\n") >= 100  # At least 100 lines

        # Test JSON export performance
        json_exporter = JSONExporter()
        json_data = json_exporter.export_networks(networks)
        json_content = json.loads(json_data.decode("utf-8"))
        assert len(json_content["data"]) == 100

    def test_large_host_import(self, client):
        """Test importing a large number of hosts."""
        # Create CSV with 50 hosts
        csv_lines = ["IP Address,Hostname,MAC Address,Status,Description"]
        for i in range(50):
            csv_lines.append(
                f"192.168.1.{i + 10},host{i:02d},aa:bb:cc:dd:ee:{i:02x},active,Host {i}"
            )
        csv_data = "\n".join(csv_lines).encode("utf-8")

        data = {
            "import_type": "hosts",
            "format_type": "csv",
            "file": (BytesIO(csv_data), "large_hosts.csv"),
        }

        response = client.post("/import", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Successfully imported 50 hosts!" in response.data

        # Verify all hosts were imported
        with client.application.app_context():
            host_count = Host.query.count()
            assert host_count >= 50
