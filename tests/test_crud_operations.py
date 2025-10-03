"""Tests for CRUD operations on networks and hosts."""

import pytest

from ipam.extensions import db
from ipam.models import Host, Network


class TestNetworkCRUD:
    """Test Create, Read, Update, Delete operations for networks."""

    def test_edit_network_page_loads(self, client):
        """Test that edit network page loads correctly."""
        with client.application.app_context():
            network = Network(
                network="192.168.100.0",
                cidr=24,
                broadcast_address="192.168.100.255",
                vlan_id=100,
                location="Test Location",
                description="Test network",
            )
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        response = client.get(f"/edit_network/{network_id}")
        assert response.status_code == 200
        assert b"Edit Network" in response.data
        assert b"192.168.100.0" in response.data
        assert b"Test Location" in response.data

    def test_edit_network_form_submission(self, client):
        """Test editing a network via form submission."""
        with client.application.app_context():
            network = Network(
                network="192.168.101.0",
                cidr=24,
                broadcast_address="192.168.101.255",
            )
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        # Submit edit form
        data = {
            "network": "192.168.101.0",
            "cidr": 25,
            "vlan_id": 200,
            "location": "Updated Location",
            "description": "Updated description",
        }

        response = client.post(
            f"/edit_network/{network_id}", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Network updated successfully!" in response.data

        # Verify changes
        with client.application.app_context():
            updated_network = db.session.get(Network, network_id)
            assert updated_network.cidr == 25
            assert updated_network.vlan_id == 200
            assert updated_network.location == "Updated Location"
            assert updated_network.description == "Updated description"

    def test_delete_network_success(self, client):
        """Test deleting a network without hosts."""
        with client.application.app_context():
            network = Network(
                network="192.168.102.0",
                cidr=24,
                broadcast_address="192.168.102.255",
            )
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        response = client.post(
            f"/delete_network/{network_id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Network deleted successfully!" in response.data

        # Verify deletion
        with client.application.app_context():
            deleted_network = db.session.get(Network, network_id)
            assert deleted_network is None

    def test_delete_network_with_hosts_fails(self, client):
        """Test that deleting a network with hosts fails."""
        with client.application.app_context():
            network = Network(
                network="192.168.103.0",
                cidr=24,
                broadcast_address="192.168.103.255",
            )
            db.session.add(network)
            db.session.commit()

            # Add a host to the network
            host = Host(
                ip_address="192.168.103.10",
                hostname="test-host",
                network_id=network.id,
            )
            db.session.add(host)
            db.session.commit()
            network_id = network.id

        response = client.post(
            f"/delete_network/{network_id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Cannot delete network: 1 hosts are still assigned"
            in response.data
        )

        # Verify network still exists
        with client.application.app_context():
            existing_network = db.session.get(Network, network_id)
            assert existing_network is not None

    def test_edit_network_404(self, client):
        """Test editing non-existent network returns 404."""
        response = client.get("/edit_network/99999")
        assert response.status_code == 404

    def test_delete_network_404(self, client):
        """Test deleting non-existent network returns 404."""
        response = client.post("/delete_network/99999")
        assert response.status_code == 404


class TestHostCRUD:
    """Test Create, Read, Update, Delete operations for hosts."""

    def test_edit_host_page_loads(self, client):
        """Test that edit host page loads correctly."""
        with client.application.app_context():
            host = Host(
                ip_address="192.168.104.10",
                hostname="test-host",
                mac_address="aa:bb:cc:dd:ee:ff",
                status="active",
                description="Test host",
            )
            db.session.add(host)
            db.session.commit()
            host_id = host.id

        response = client.get(f"/edit_host/{host_id}")
        assert response.status_code == 200
        assert b"Edit Host" in response.data
        assert b"192.168.104.10" in response.data
        assert b"test-host" in response.data

    def test_edit_host_form_submission(self, client):
        """Test editing a host via form submission."""
        with client.application.app_context():
            host = Host(
                ip_address="192.168.105.10",
                hostname="old-hostname",
                status="active",
            )
            db.session.add(host)
            db.session.commit()
            host_id = host.id

        # Submit edit form
        data = {
            "ip_address": "192.168.105.11",
            "hostname": "new-hostname",
            "mac_address": "bb:cc:dd:ee:ff:aa",
            "status": "reserved",
            "network_id": 0,  # Auto-detect
            "description": "Updated host description",
        }

        response = client.post(
            f"/edit_host/{host_id}", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Host updated successfully!" in response.data

        # Verify changes
        with client.application.app_context():
            updated_host = db.session.get(Host, host_id)
            assert updated_host.ip_address == "192.168.105.11"
            assert updated_host.hostname == "new-hostname"
            assert updated_host.mac_address == "bb:cc:dd:ee:ff:aa"
            assert updated_host.status == "reserved"
            assert updated_host.description == "Updated host description"

    def test_delete_host_success(self, client):
        """Test deleting a host."""
        with client.application.app_context():
            host = Host(ip_address="192.168.106.10", hostname="delete-me")
            db.session.add(host)
            db.session.commit()
            host_id = host.id

        response = client.post(f"/delete_host/{host_id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"Host deleted successfully!" in response.data

        # Verify deletion
        with client.application.app_context():
            deleted_host = db.session.get(Host, host_id)
            assert deleted_host is None

    def test_edit_host_with_network(self, client):
        """Test editing a host and assigning it to a specific network."""
        with client.application.app_context():
            # Create network
            network = Network(
                network="192.168.107.0",
                cidr=24,
                broadcast_address="192.168.107.255",
            )
            db.session.add(network)
            db.session.commit()

            # Create host
            host = Host(ip_address="192.168.107.10")
            db.session.add(host)
            db.session.commit()

            host_id = host.id
            network_id = network.id

        # Edit host and assign to network
        data = {
            "ip_address": "192.168.107.10",
            "hostname": "assigned-host",
            "mac_address": "",
            "status": "active",
            "network_id": network_id,
            "description": "",
        }

        response = client.post(
            f"/edit_host/{host_id}", data=data, follow_redirects=True
        )
        assert response.status_code == 200

        # Verify network assignment
        with client.application.app_context():
            updated_host = db.session.get(Host, host_id)
            assert updated_host.network_id == network_id
            assert updated_host.hostname == "assigned-host"

    def test_edit_host_404(self, client):
        """Test editing non-existent host returns 404."""
        response = client.get("/edit_host/99999")
        assert response.status_code == 404

    def test_delete_host_404(self, client):
        """Test deleting non-existent host returns 404."""
        response = client.post("/delete_host/99999")
        assert response.status_code == 404


class TestFormValidation:
    """Test form validation for edit operations."""

    def test_edit_network_invalid_data(self, client):
        """Test editing network with invalid data."""
        with client.application.app_context():
            network = Network(
                network="192.168.108.0",
                cidr=24,
                broadcast_address="192.168.108.255",
            )
            db.session.add(network)
            db.session.commit()
            network_id = network.id

        # Submit invalid data
        data = {
            "network": "invalid-network",
            "cidr": 33,  # Invalid CIDR
            "vlan_id": "",
            "location": "",
            "description": "",
        }

        response = client.post(f"/edit_network/{network_id}", data=data)
        assert response.status_code == 200
        assert b"Invalid network" in response.data

    def test_edit_host_invalid_ip(self, client):
        """Test editing host with invalid IP address."""
        with client.application.app_context():
            host = Host(ip_address="192.168.109.10")
            db.session.add(host)
            db.session.commit()
            host_id = host.id

        # Submit invalid IP
        data = {
            "ip_address": "invalid.ip.address",
            "hostname": "test",
            "mac_address": "",
            "status": "active",
            "network_id": 0,
            "description": "",
        }

        response = client.post(f"/edit_host/{host_id}", data=data)
        assert response.status_code == 200
        # Form should redisplay with validation errors
        assert b"Edit Host" in response.data
