import json
import pytest
from io import BytesIO

from app import app, db, Network, Host
from exporters.csv_exporter import CSVExporter
from exporters.json_exporter import JSONExporter
from importers.csv_importer import CSVImporter


class TestExporters:
    def test_csv_exporter_networks(self, app_context):
        """Test CSV export for networks."""
        # Create test networks
        network1 = Network(
            network="192.168.1.0",
            cidr=24,
            broadcast_address="192.168.1.255",
            vlan_id=100,
            description="Test network 1",
            location="Office",
        )
        network2 = Network(
            network="10.0.0.0", cidr=16, broadcast_address="10.0.255.255"
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
        assert "192.168.1.0,24,192.168.1.255" in csv_content
        assert "10.0.0.0,16,10.0.255.255" in csv_content

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
        assert (
            response.headers["Content-Type"]
            == "application/json; charset=utf-8"
        )
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
