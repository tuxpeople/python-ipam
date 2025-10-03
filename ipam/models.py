"""SQLAlchemy models."""

import ipaddress

from ipam.extensions import db


class Network(db.Model):
    """Network model."""

    __tablename__ = "networks"

    id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(18), nullable=False, unique=True)
    cidr = db.Column(db.Integer, nullable=False)
    broadcast_address = db.Column(db.String(15))
    name = db.Column(db.String(100))
    domain = db.Column(db.String(100))
    vlan_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))

    hosts = db.relationship(
        "Host", backref="network_ref", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Network {self.network}/{self.cidr}>"

    @property
    def network_address(self):
        network = ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        )
        return str(network.network_address)

    @property
    def total_hosts(self):
        network = ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        )
        return len(list(network.hosts()))

    @property
    def used_hosts(self):
        return len(self.hosts)

    @property
    def available_hosts(self):
        return self.total_hosts - self.used_hosts


class Host(db.Model):
    """Host model."""

    __tablename__ = "hosts"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False, unique=True)
    hostname = db.Column(db.String(255))
    cname = db.Column(db.String(255))
    mac_address = db.Column(db.String(17))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")
    network_id = db.Column(
        db.Integer, db.ForeignKey("networks.id"), nullable=True
    )

    def __repr__(self):
        return f"<Host {self.ip_address}>"
