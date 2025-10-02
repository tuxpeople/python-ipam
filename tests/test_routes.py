import pytest
import json
from app import db, Network, Host


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
