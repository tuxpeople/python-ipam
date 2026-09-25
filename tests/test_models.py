"""Test database models."""

import pytest
from sqlalchemy.exc import IntegrityError

from ipam.extensions import db
from ipam.models import DhcpRange, Host, Network


class TestNetworkModel:
    def test_network_creation(self, app_context):
        network = Network(
            network="192.168.1.0",
            cidr=24,
            broadcast_address="192.168.1.255",
            vlan_id=100,
            description="Test network",
            location="Test location",
        )
        db.session.add(network)
        db.session.commit()

        assert network.id is not None
        assert network.network == "192.168.1.0"
        assert network.cidr == 24
        assert network.vlan_id == 100

    def test_network_properties(self, app_context):
        network = Network(
            network="192.168.1.0", cidr=24, broadcast_address="192.168.1.255"
        )
        db.session.add(network)
        db.session.commit()

        assert network.network_address == "192.168.1.0"
        assert network.total_hosts == 254
        assert network.used_hosts == 0
        assert network.available_hosts == 254

    def test_network_with_hosts(self, app_context):
        network = Network(
            network="192.168.1.0", cidr=24, broadcast_address="192.168.1.255"
        )
        db.session.add(network)
        db.session.commit()

        host1 = Host(
            ip_address="192.168.1.10", hostname="test1", network_id=network.id
        )
        host2 = Host(
            ip_address="192.168.1.11", hostname="test2", network_id=network.id
        )
        db.session.add(host1)
        db.session.add(host2)
        db.session.commit()

        assert network.used_hosts == 2
        assert network.available_hosts == 252

    def test_network_unique_constraint(self, app_context):
        network1 = Network(network="192.168.1.0", cidr=24)
        network2 = Network(network="192.168.1.0", cidr=24)

        db.session.add(network1)
        db.session.commit()

        db.session.add(network2)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_network_cascade_delete(self, app_context):
        network = Network(network="192.168.1.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        host = Host(ip_address="192.168.1.10", network_id=network.id)
        db.session.add(host)
        db.session.commit()

        network_id = network.id
        db.session.delete(network)
        db.session.commit()

        remaining_hosts = Host.query.filter_by(network_id=network_id).all()
        assert len(remaining_hosts) == 0

    def test_find_for_ip_prefers_most_specific_network(self, app_context):
        """With overlapping networks, the narrowest one wins."""
        wide = Network(
            network="10.0.0.0", cidr=16, broadcast_address="10.0.255.255"
        )
        narrow = Network(
            network="10.0.1.0", cidr=24, broadcast_address="10.0.1.255"
        )
        db.session.add_all([wide, narrow])
        db.session.commit()

        found = Network.find_for_ip("10.0.1.5")
        assert found.id == narrow.id

    def test_find_for_ip_falls_back_to_only_match(self, app_context):
        wide = Network(
            network="10.0.0.0", cidr=16, broadcast_address="10.0.255.255"
        )
        db.session.add(wide)
        db.session.commit()

        found = Network.find_for_ip("10.0.1.5")
        assert found.id == wide.id

    def test_find_for_ip_no_match(self, app_context):
        assert Network.find_for_ip("192.168.99.1") is None

    def test_find_overlapping_detects_supernet_and_subnet(self, app_context):
        existing = Network(
            network="10.10.0.0", cidr=16, broadcast_address="10.10.255.255"
        )
        db.session.add(existing)
        db.session.commit()

        # A /24 fully inside the existing /16 overlaps.
        assert Network.find_overlapping("10.10.5.0", 24).id == existing.id
        # A /15 that would contain the existing /16 also overlaps.
        assert Network.find_overlapping("10.10.0.0", 15).id == existing.id

    def test_find_overlapping_no_overlap(self, app_context):
        existing = Network(
            network="10.10.0.0", cidr=24, broadcast_address="10.10.0.255"
        )
        db.session.add(existing)
        db.session.commit()

        assert Network.find_overlapping("10.11.0.0", 24) is None

    def test_find_overlapping_excludes_given_id(self, app_context):
        existing = Network(
            network="10.10.0.0", cidr=24, broadcast_address="10.10.0.255"
        )
        db.session.add(existing)
        db.session.commit()

        assert (
            Network.find_overlapping("10.10.0.0", 24, exclude_id=existing.id)
            is None
        )


class TestHostModel:
    def test_host_creation(self, app_context):
        host = Host(
            ip_address="192.168.1.10",
            hostname="test-host",
            mac_address="aa:bb:cc:dd:ee:ff",
            description="Test host",
            status="active",
        )
        db.session.add(host)
        db.session.commit()

        assert host.id is not None
        assert host.ip_address == "192.168.1.10"
        assert host.hostname == "test-host"
        assert host.status == "active"

    def test_host_unique_ip(self, app_context):
        host1 = Host(ip_address="192.168.1.10")
        host2 = Host(ip_address="192.168.1.10")

        db.session.add(host1)
        db.session.commit()

        db.session.add(host2)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_host_default_status(self, app_context):
        host = Host(ip_address="192.168.1.10")
        db.session.add(host)
        db.session.commit()

        assert host.status == "active"

    def test_host_network_relationship(self, app_context):
        network = Network(network="192.168.1.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        host = Host(ip_address="192.168.1.10", network_id=network.id)
        db.session.add(host)
        db.session.commit()

        assert host.network_ref == network
        assert host in network.hosts


class TestDhcpRangeModel:
    def test_dhcp_range_creation(self, app_context):
        network = Network(network="10.0.0.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        dhcp_range = DhcpRange(
            network_id=network.id,
            start_ip="10.0.0.10",
            end_ip="10.0.0.50",
            description="Test range",
            is_active=True,
        )
        db.session.add(dhcp_range)
        db.session.commit()

        assert dhcp_range.id is not None
        assert dhcp_range.network_ref == network
        assert dhcp_range.start_ip == "10.0.0.10"

    def test_dhcp_range_cascade_delete(self, app_context):
        network = Network(network="10.0.1.0", cidr=24)
        db.session.add(network)
        db.session.commit()

        dhcp_range = DhcpRange(
            network_id=network.id,
            start_ip="10.0.1.10",
            end_ip="10.0.1.20",
        )
        db.session.add(dhcp_range)
        db.session.commit()

        range_id = dhcp_range.id
        db.session.delete(network)
        db.session.commit()

        assert DhcpRange.query.filter_by(id=range_id).first() is None
