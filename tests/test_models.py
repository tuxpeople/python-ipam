"""Test database models."""

import ipaddress

import pytest

from ipam.extensions import db
from ipam.models import Host, Network


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
        with pytest.raises(Exception):
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
        with pytest.raises(Exception):
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
