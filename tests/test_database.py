"""Test database initialization and table creation."""

import os
import tempfile

import pytest

from ipam import create_app
from ipam.extensions import db
from ipam.models import DhcpRange, Host, Network


class TestDatabaseInitialization:
    """Test database creation and schema."""

    def test_database_tables_created(self):
        """Test that all required tables are created."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        # Create app with temporary database
        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            # Create all tables
            db.create_all()

            # Get all table names
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            # Verify required tables exist
            assert "networks" in tables
            assert "hosts" in tables

            # Clean up
            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)

    def test_network_table_schema(self):
        """Test that network table has correct columns."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            db.create_all()

            # Get network table columns
            inspector = db.inspect(db.engine)
            columns = [c["name"] for c in inspector.get_columns("networks")]

            # Verify required columns exist
            required_columns = [
                "id",
                "network",
                "cidr",
                "broadcast_address",
                "name",
                "domain",
                "vlan_id",
                "description",
                "location",
            ]

            for col in required_columns:
                assert (
                    col in columns
                ), f"Column '{col}' missing from networks table"

            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)

    def test_host_table_schema(self):
        """Test that host table has correct columns."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            db.create_all()

            # Get host table columns
            inspector = db.inspect(db.engine)
            columns = [c["name"] for c in inspector.get_columns("hosts")]

            # Verify required columns exist
            required_columns = [
                "id",
                "ip_address",
                "hostname",
                "cname",
                "mac_address",
                "description",
                "status",
                "network_id",
            ]

            for col in required_columns:
                assert (
                    col in columns
                ), f"Column '{col}' missing from hosts table"

            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)

    def test_dhcp_range_table_schema(self):
        """Test that DHCP ranges table has correct columns."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            db.create_all()

            inspector = db.inspect(db.engine)
            columns = [c["name"] for c in inspector.get_columns("dhcp_ranges")]

            required_columns = [
                "id",
                "network_id",
                "start_ip",
                "end_ip",
                "description",
                "is_active",
            ]

            for col in required_columns:
                assert (
                    col in columns
                ), f"Column '{col}' missing from dhcp_ranges table"

            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)

    def test_database_relationships(self):
        """Test that database relationships work correctly."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            db.create_all()

            # Create a network
            network = Network(
                network="192.168.1.0",
                cidr=24,
                broadcast_address="192.168.1.255",
                name="Test Network",
            )
            db.session.add(network)
            db.session.commit()

            # Create a host in that network
            host = Host(
                ip_address="192.168.1.10",
                hostname="test-host",
                network_id=network.id,
            )
            db.session.add(host)
            db.session.commit()

            # Verify relationship works
            assert len(network.hosts) == 1
            assert network.hosts[0].hostname == "test-host"
            assert host.network_ref.name == "Test Network"

            # Create DHCP range for network
            dhcp_range = DhcpRange(
                network_id=network.id,
                start_ip="192.168.1.50",
                end_ip="192.168.1.100",
            )
            db.session.add(dhcp_range)
            db.session.commit()

            assert len(network.dhcp_ranges) == 1
            assert network.dhcp_ranges[0].start_ip == "192.168.1.50"
            assert dhcp_range.network_ref.name == "Test Network"

            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)

    def test_cascade_delete(self):
        """Test that deleting a network cascades to hosts."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        app = create_app("default")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["TESTING"] = True

        with app.app_context():
            db.create_all()

            # Create network with hosts
            network = Network(
                network="192.168.2.0",
                cidr=24,
                broadcast_address="192.168.2.255",
            )
            db.session.add(network)
            db.session.commit()

            host1 = Host(ip_address="192.168.2.10", network_id=network.id)
            host2 = Host(ip_address="192.168.2.11", network_id=network.id)
            db.session.add_all([host1, host2])
            db.session.commit()

            network_id = network.id
            host_ids = [host1.id, host2.id]

            # Delete network
            db.session.delete(network)
            db.session.commit()

            # Verify hosts were also deleted (cascade)
            assert db.session.get(Network, network_id) is None
            for host_id in host_ids:
                assert db.session.get(Host, host_id) is None

            db.drop_all()

        os.close(db_fd)
        os.unlink(db_path)
