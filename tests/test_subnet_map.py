"""Tests for the per-address subnet map (IPAM-028)."""

from datetime import timedelta

from ipam.allocation import utcnow
from ipam.extensions import db
from ipam.models import DhcpRange, Host, Network
from ipam.subnet_map import (
    BLOCK_SIZE,
    CATEGORY_DYNAMIC,
    CATEGORY_FREE,
    CATEGORY_NETWORK,
    CATEGORY_PERSISTENT,
    CATEGORY_POOL,
    CATEGORY_RECORDED,
    block_for_ip,
    build_subnet_map,
)


def _network(address, cidr):
    network = Network(network=address, cidr=cidr)
    db.session.add(network)
    db.session.commit()
    return network


def _categories(subnet_map):
    return {cell["ip"]: cell["category"] for cell in subnet_map["cells"]}


class TestBuildSubnetMap:
    def test_categories_for_slash_24(self, app_context):
        network = _network("192.168.50.0", 24)
        now = utcnow()
        db.session.add_all(
            [
                Host(
                    ip_address="192.168.50.2",
                    network_id=network.id,
                    assignment_type="reservation",
                ),
                Host(
                    ip_address="192.168.50.3",
                    network_id=network.id,
                    assignment_type="static",
                ),
                Host(
                    ip_address="192.168.50.120",
                    network_id=network.id,
                    assignment_type="dynamic",
                    lease_expires_at=now + timedelta(hours=1),
                ),
                Host(
                    ip_address="192.168.50.121",
                    network_id=network.id,
                    lease_expires_at=now - timedelta(hours=1),
                ),
                Host(ip_address="192.168.50.4", network_id=network.id),
                DhcpRange(
                    network_id=network.id,
                    start_ip="192.168.50.100",
                    end_ip="192.168.50.199",
                ),
                DhcpRange(
                    network_id=network.id,
                    start_ip="192.168.50.200",
                    end_ip="192.168.50.209",
                    is_active=False,
                ),
            ]
        )
        db.session.commit()

        subnet_map = build_subnet_map(network, now=now)
        categories = _categories(subnet_map)

        assert len(subnet_map["cells"]) == 256
        assert subnet_map["block_count"] == 1
        assert subnet_map["overview"] is None
        assert categories["192.168.50.0"] == CATEGORY_NETWORK
        assert categories["192.168.50.255"] == CATEGORY_NETWORK
        labels = {c["ip"]: c["state_label"] for c in subnet_map["cells"]}
        assert labels["192.168.50.0"] == "Network address"
        assert labels["192.168.50.255"] == "Broadcast address"
        assert subnet_map["columns_wide"] == 32
        assert categories["192.168.50.2"] == CATEGORY_PERSISTENT
        assert categories["192.168.50.3"] == CATEGORY_PERSISTENT
        assert categories["192.168.50.4"] == CATEGORY_RECORDED
        assert categories["192.168.50.120"] == CATEGORY_DYNAMIC
        # Expired lease inside the pool still shows the record.
        assert categories["192.168.50.121"] == CATEGORY_RECORDED
        assert categories["192.168.50.100"] == CATEGORY_POOL
        # Inactive ranges are not pools.
        assert categories["192.168.50.200"] == CATEGORY_FREE
        assert categories["192.168.50.1"] == CATEGORY_FREE
        assert subnet_map["counts"][CATEGORY_POOL] == 98

    def test_small_networks(self, app_context):
        slash_28 = build_subnet_map(_network("10.1.0.0", 28))
        assert len(slash_28["cells"]) == 16
        assert slash_28["columns"] == 16
        assert slash_28["columns_wide"] == 16

        slash_31 = build_subnet_map(_network("10.2.0.0", 31))
        assert [c["category"] for c in slash_31["cells"]] == [
            CATEGORY_FREE,
            CATEGORY_FREE,
        ]
        assert slash_31["columns"] == 2

        slash_32 = build_subnet_map(_network("10.3.0.1", 32))
        assert [c["category"] for c in slash_32["cells"]] == [CATEGORY_FREE]

    def test_large_network_blocks_and_overview(self, app_context):
        network = _network("10.20.0.0", 16)
        db.session.add_all(
            [
                Host(ip_address="10.20.5.10", network_id=network.id),
                Host(ip_address="10.20.5.11", network_id=network.id),
                # Host inside the pool must not be counted twice.
                Host(ip_address="10.20.7.5", network_id=network.id),
                DhcpRange(
                    network_id=network.id,
                    start_ip="10.20.6.200",
                    end_ip="10.20.7.9",
                ),
            ]
        )
        db.session.commit()

        subnet_map = build_subnet_map(network, block=5)
        assert subnet_map["block_count"] == 256
        assert subnet_map["block_start"] == "10.20.5.0"
        assert subnet_map["block_end"] == "10.20.5.255"
        assert len(subnet_map["cells"]) == BLOCK_SIZE
        assert subnet_map["counts"][CATEGORY_RECORDED] == 2
        # Network/broadcast only appear in the first/last block.
        assert subnet_map["counts"][CATEGORY_NETWORK] == 0

        overview = subnet_map["overview"]
        assert len(overview) == 256
        assert overview[5]["used"] == 2
        assert overview[6]["used"] == 56
        assert overview[7]["used"] == 10
        assert overview[0]["used"] == 0

    def test_block_is_clamped(self, app_context):
        network = _network("10.30.0.0", 23)
        assert build_subnet_map(network, block=99)["block"] == 1
        assert build_subnet_map(network, block=-3)["block"] == 0

    def test_very_large_network_has_no_overview(self, app_context):
        network = _network("10.0.0.0", 8)
        subnet_map = build_subnet_map(network, block=65535)
        assert subnet_map["block_count"] == 65536
        assert subnet_map["overview"] is None
        assert subnet_map["block_end"] == "10.255.255.255"
        assert subnet_map["cells"][-1]["state_label"] == "Broadcast address"

    def test_block_for_ip(self, app_context):
        network = _network("10.40.0.0", 16)
        assert block_for_ip(network, "10.40.3.7") == 3
        assert block_for_ip(network, "10.41.0.1") is None
        assert block_for_ip(network, "garbage") is None


class TestSubnetMapView:
    def test_detail_page_renders_map(self, client):
        with client.application.app_context():
            network = _network("192.168.60.0", 24)
            host = Host(
                ip_address="192.168.60.5",
                hostname="printer",
                mac_address="aa:bb:cc:dd:ee:05",
                network_id=network.id,
            )
            db.session.add(host)
            db.session.commit()
            network_id, host_id = network.id, host.id

        html = client.get(f"/networks/{network_id}").data
        assert b"Address Map" in html
        assert f'href="/hosts/{host_id}"'.encode() in html
        assert b"Hostname: printer" in html
        assert b"MAC: aa:bb:cc:dd:ee:05" in html
        assert (
            b"/add_host?ip_address=192.168.60.6&amp;network_id="
            + str(network_id).encode()
        ) in html

    def test_jump_to_ip_selects_block(self, client):
        with client.application.app_context():
            network_id = _network("10.50.0.0", 22).id

        html = client.get(f"/networks/{network_id}?ip=10.50.2.9").data
        assert b"10.50.2.0 \xe2\x80\x93 10.50.2.255" in html

        html = client.get(
            f"/networks/{network_id}?ip=8.8.8.8", follow_redirects=True
        ).data
        assert b"8.8.8.8 is not an address in this network" in html

    def test_add_host_prefill(self, client):
        with client.application.app_context():
            network_id = _network("192.168.61.0", 24).id

        html = client.get(
            f"/add_host?ip_address=192.168.61.7&network_id={network_id}"
        ).data
        assert b'value="192.168.61.7"' in html
        assert f'<option selected value="{network_id}">'.encode() in html
