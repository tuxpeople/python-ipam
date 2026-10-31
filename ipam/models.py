"""SQLAlchemy models."""

import ipaddress

from ipam.allocation import (
    allocation_label,
    derive_allocation_state,
    lease_is_active,
)
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
    dhcp_ranges = db.relationship(
        "DhcpRange",
        backref="network_ref",
        lazy=True,
        cascade="all, delete-orphan",
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
        """Number of addresses that would be offered for allocation.

        Uses the same semantics as :meth:`allocatable_addresses`.
        """
        return sum(1 for _ in self.allocatable_addresses())

    def allocatable_addresses(self):
        """Yield addresses that may be suggested for static allocation.

        An address is excluded when any host record exists for it
        (whatever its assignment, lease or observation state: an expired
        lease or missed ping is not proof that it is free) or when it
        lies inside an active DHCP range. A yielded address only has *no
        recorded allocation*; it is not positively confirmed free.
        """
        net = ipaddress.IPv4Network(f"{self.network}/{self.cidr}", strict=False)
        recorded = {ipaddress.IPv4Address(h.ip_address) for h in self.hosts}
        pools = [
            (
                ipaddress.IPv4Address(r.start_ip),
                ipaddress.IPv4Address(r.end_ip),
            )
            for r in self.dhcp_ranges
            if r.is_active
        ]
        for ip in net.hosts():
            if ip in recorded:
                continue
            if any(start <= ip <= end for start, end in pools):
                continue
            yield ip

    @classmethod
    def find_for_ip(cls, ip_address):
        """Return the most specific network containing an IPv4 address.

        If multiple networks contain the address (overlapping or
        nested networks), the one with the highest CIDR (narrowest
        range) wins.
        """
        ip = ipaddress.IPv4Address(ip_address)
        best = None
        for net in cls.query.all():
            net_obj = ipaddress.IPv4Network(
                f"{net.network}/{net.cidr}", strict=False
            )
            if ip in net_obj and (best is None or net.cidr > best.cidr):
                best = net
        return best

    @classmethod
    def find_overlapping(cls, network_address, cidr, exclude_id=None):
        """Return an existing network whose range overlaps the given
        network/cidr, if any."""
        candidate = ipaddress.IPv4Network(
            f"{network_address}/{cidr}", strict=False
        )
        query = cls.query
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
        for net in query.all():
            net_obj = ipaddress.IPv4Network(
                f"{net.network}/{net.cidr}", strict=False
            )
            if candidate.overlaps(net_obj):
                return net
        return None


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
    last_seen = db.Column(db.DateTime)
    discovery_source = db.Column(db.String(50))
    # Legacy curation flag. Not authoritative for allocation; see
    # ``allocation_state`` and ADDRESS_ASSIGNMENT_MODEL.md.
    is_assigned = db.Column(db.Boolean, default=False, nullable=False)
    network_id = db.Column(
        db.Integer, db.ForeignKey("networks.id"), nullable=True
    )

    # Assignment aspect: how the address is allocated.
    assignment_type = db.Column(db.String(20))
    assignment_source = db.Column(db.String(50))
    assignment_last_confirmed_at = db.Column(db.DateTime)
    # Lease aspect: an explicitly observed DHCP lease.
    lease_expires_at = db.Column(db.DateTime)
    lease_source = db.Column(db.String(50))
    lease_observed_at = db.Column(db.DateTime)
    # Observation aspect: provenance of ``last_seen``.
    last_seen_source = db.Column(db.String(50))

    def __repr__(self):
        return f"<Host {self.ip_address}>"

    @property
    def lease_active(self):
        """True if an explicitly observed lease has not yet expired."""
        return lease_is_active(self)

    @property
    def allocation_state(self):
        """Allocation state derived from assignment, lease and observation."""
        return derive_allocation_state(self)

    @property
    def allocation_label(self):
        """Human readable form of :attr:`allocation_state`."""
        return allocation_label(self.allocation_state)


class DhcpRange(db.Model):
    """DHCP range model."""

    __tablename__ = "dhcp_ranges"

    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(
        db.Integer, db.ForeignKey("networks.id"), nullable=False
    )
    start_ip = db.Column(db.String(15), nullable=False)
    end_ip = db.Column(db.String(15), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<DhcpRange {self.start_ip}-{self.end_ip}>"
