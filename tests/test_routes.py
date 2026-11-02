"""Test web routes."""

import json
import os
from datetime import datetime

from ipam.extensions import db
from ipam.models import Host, Network


class TestIndexRoute:
    def test_index_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"IPAM Dashboard" in response.data

    def test_index_with_data(self, client):
        with client.application.app_context():
            network = Network(network="192.168.1.0", cidr=24)
            db.session.add(network)
            db.session.commit()

            host = Host(ip_address="192.168.1.10", network_id=network.id)
            db.session.add(host)
            db.session.commit()

        response = client.get("/")
        assert response.status_code == 200
        assert b"192.168.1.0" in response.data


class TestAppVersion:
    def test_version_from_version_file(self):
        from ipam.config import Config, _version_from_file

        with open(
            os.path.join(Config.BASE_DIR, "version.txt"), encoding="utf-8"
        ) as version_file:
            expected = version_file.read().strip()
        assert _version_from_file(Config.BASE_DIR) == expected

    def test_missing_version_file(self, tmp_path):
        from ipam.config import _version_from_file

        assert _version_from_file(str(tmp_path)) == ""

    def test_version_shown_in_footer(self, client):
        client.application.config["APP_VERSION"] = "9.9.9"
        response = client.get("/")
        assert response.status_code == 200
        assert b"Python IPAM v9.9.9" in response.data


class TestNetworkRoutes:
    def test_networks_page(self, client):
        response = client.get("/networks")
        assert response.status_code == 200
        assert b"Networks" in response.data

    def test_add_network_get(self, client):
        response = client.get("/add_network")
        assert response.status_code == 200
        assert b"Add New Network" in response.data

    def test_add_network_post_valid(self, client):
        data = {
            "network": "192.168.1.0",
            "cidr": 24,
            "vlan_id": 100,
            "description": "Test network",
            "location": "Test location",
        }
        response = client.post("/add_network", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Network added successfully!" in response.data

        with client.application.app_context():
            network = Network.query.filter_by(network="192.168.1.0").first()
            assert network is not None
            assert network.cidr == 24
            assert network.vlan_id == 100

    def test_add_network_post_invalid(self, client):
        data = {"network": "invalid-ip", "cidr": 24}
        response = client.post("/add_network", data=data)
        assert response.status_code == 200
        assert b"Invalid network" in response.data

    def test_add_network_duplicate(self, client):
        with client.application.app_context():
            network = Network(network="192.168.1.0", cidr=24)
            db.session.add(network)
            db.session.commit()

        data = {"network": "192.168.1.0", "cidr": 24}
        response = client.post("/add_network", data=data)
        assert response.status_code == 200


class TestHostRoutes:
    def test_hosts_last_seen_column(self, client):
        """Show sortable timestamps and a placeholder for unseen hosts."""
        with client.application.app_context():
            db.session.add_all(
                [
                    Host(
                        ip_address="10.42.0.10",
                        last_seen=datetime(2026, 9, 25, 8, 5, 3),
                    ),
                    Host(ip_address="10.42.0.11"),
                ]
            )
            db.session.commit()
        response = client.get("/hosts")
        assert response.status_code == 200
        assert b"<th>Last Seen</th>" in response.data
        assert b'data-order="2026-09-25 08:05:03"' in response.data
        assert b"2026-09-25 08:05:03\n" in response.data
        assert b'data-order="">\n                        -\n' in response.data
        assert b"targets: [-1], orderable: false" in response.data

    def test_hosts_page(self, client):
        response = client.get("/hosts")
        assert response.status_code == 200
        assert b"Hosts" in response.data

    def test_add_host_get(self, client):
        response = client.get("/add_host")
        assert response.status_code == 200
        assert b"Add New Host" in response.data

    def test_add_host_post_valid(self, client):
        data = {
            "ip_address": "192.168.1.10",
            "hostname": "test-host",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "description": "Test host",
            "status": "active",
            "network_id": 0,
        }
        response = client.post("/add_host", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Host added successfully!" in response.data

        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host is not None
            assert host.hostname == "test-host"
            assert host.status == "active"

    def test_add_host_with_network(self, client):
        with client.application.app_context():
            network = Network(network="192.168.1.0", cidr=24)
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        data = {
            "ip_address": "192.168.1.10",
            "hostname": "test-host",
            "status": "active",
            "network_id": network_id,
        }
        response = client.post("/add_host", data=data, follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host.network_id == network_id

    def test_add_host_auto_detect_network(self, client):
        with client.application.app_context():
            network = Network(network="192.168.1.0", cidr=24)
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        data = {
            "ip_address": "192.168.1.10",
            "hostname": "test-host",
            "status": "active",
            "network_id": 0,
        }
        response = client.post("/add_host", data=data, follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            host = Host.query.filter_by(ip_address="192.168.1.10").first()
            assert host.network_id == network_id

    def test_add_host_invalid_ip(self, client):
        data = {"ip_address": "invalid-ip", "status": "active", "network_id": 0}
        response = client.post("/add_host", data=data)
        assert response.status_code == 200


class TestAPIRoutes:
    def test_api_networks(self, client):
        with client.application.app_context():
            network = Network(
                network="192.168.1.0",
                cidr=24,
                vlan_id=100,
                description="Test network",
            )
            db.session.add(network)
            db.session.commit()

        response = client.get("/api/networks")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["network"] == "192.168.1.0"
        assert data[0]["cidr"] == 24
        assert data[0]["vlan_id"] == 100

    def test_api_hosts(self, client):
        with client.application.app_context():
            host = Host(
                ip_address="192.168.1.10", hostname="test-host", status="active"
            )
            db.session.add(host)
            db.session.commit()

        response = client.get("/api/hosts")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["ip_address"] == "192.168.1.10"
        assert data[0]["hostname"] == "test-host"
        assert data[0]["status"] == "active"

    def test_api_empty_response(self, client):
        response = client.get("/api/networks")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

        response = client.get("/api/hosts")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []


class TestIpSortKey:
    def test_orders_numerically(self):
        from ipam.web.routes import ip_sort_key

        ips = ["10.0.0.10", "10.0.0.2", "9.255.255.255", "192.168.1.1"]
        assert sorted(ips, key=ip_sort_key) == [
            "9.255.255.255",
            "10.0.0.2",
            "10.0.0.10",
            "192.168.1.1",
        ]

    def test_invalid_value_returned_unchanged(self):
        from ipam.web.routes import ip_sort_key

        assert ip_sort_key("not-an-ip") == "not-an-ip"
        assert ip_sort_key("") == ""

    def test_lists_render_sort_keys(self, client):
        with client.application.app_context():
            network = Network(network="10.0.0.0", cidr=24)
            db.session.add(network)
            db.session.commit()
            db.session.add(Host(ip_address="10.0.0.2", network_id=network.id))
            db.session.commit()
            network_id = network.id

        hosts = client.get("/hosts").data
        assert b'data-order="0167772162"' in hosts
        assert b'data-order="0167772160/24"' in hosts
        assert b'data-order="0167772160"' in client.get("/networks").data
        assert (
            b'data-order="0167772162"'
            in client.get(f"/networks/{network_id}").data
        )
