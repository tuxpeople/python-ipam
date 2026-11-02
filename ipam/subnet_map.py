"""Per-address subnet map for the network detail view.

The map renders data already stored in the database: host records (by
their derived allocation state), active DHCP ranges and the network and
broadcast addresses. An address without any record is shown as having
*no recorded allocation*, not as positively confirmed free.

Large networks are split into blocks of ``BLOCK_SIZE`` addresses (one
/24 each); only one block is expanded into cells at a time.
"""

import ipaddress

from ipam.allocation import (
    STATE_DYNAMIC,
    STATE_RESERVED,
    STATE_RESERVED_LEASE_ACTIVE,
    STATE_STATIC,
    allocation_label,
    derive_allocation_state,
    utcnow,
)

BLOCK_SIZE = 256

#: Networks with at most this many blocks get a clickable block overview
#: (a /16 has 256 blocks); larger networks use prev/next and jump-to-IP.
MAX_OVERVIEW_BLOCKS = 256

# Cell categories, in legend order.
CATEGORY_PERSISTENT = "persistent"
CATEGORY_DYNAMIC = "dynamic"
CATEGORY_RECORDED = "recorded"
CATEGORY_POOL = "pool"
CATEGORY_FREE = "free"
CATEGORY_NETWORK = "network"

CATEGORY_LABELS = {
    CATEGORY_PERSISTENT: "Reserved / static",
    CATEGORY_DYNAMIC: "Dynamic",
    CATEGORY_RECORDED: "Recorded, allocation not confirmed",
    CATEGORY_POOL: "DHCP pool",
    CATEGORY_FREE: "No recorded allocation",
    CATEGORY_NETWORK: "Network / broadcast address",
}

_PERSISTENT_STATES = {STATE_RESERVED, STATE_RESERVED_LEASE_ACTIVE, STATE_STATIC}


def host_category(host, now=None):
    """Return the map category for an existing host record."""
    state = derive_allocation_state(host, now)
    if state in _PERSISTENT_STATES:
        return CATEGORY_PERSISTENT
    if state == STATE_DYNAMIC:
        return CATEGORY_DYNAMIC
    # Expired lease, observation only or unknown assignment: the record
    # still blocks allocation, but nothing confirms a current allocation.
    return CATEGORY_RECORDED


def _active_pools(network, net):
    """Return active DHCP ranges as (start, end) ints clipped to ``net``."""
    first = int(net.network_address)
    last = int(net.broadcast_address)
    pools = []
    for dhcp_range in network.dhcp_ranges:
        if not dhcp_range.is_active:
            continue
        start = max(int(ipaddress.IPv4Address(dhcp_range.start_ip)), first)
        end = min(int(ipaddress.IPv4Address(dhcp_range.end_ip)), last)
        if start <= end:
            pools.append((start, end))
    return pools


def _in_pools(value, pools):
    return any(start <= value <= end for start, end in pools)


def block_for_ip(network, ip_address):
    """Return the block index containing ``ip_address``, or None."""
    net = ipaddress.IPv4Network(
        f"{network.network}/{network.cidr}", strict=False
    )
    try:
        ip = ipaddress.IPv4Address(ip_address)
    except ValueError:
        return None
    if ip not in net:
        return None
    return (int(ip) - int(net.network_address)) // BLOCK_SIZE


def build_subnet_map(network, block=0, now=None):
    """Build the subnet map for one block of ``network``.

    Returns a dict with the cells of the selected block, per-category
    counts for that block, pagination data and, for networks of up to
    ``MAX_OVERVIEW_BLOCKS`` blocks, an occupancy overview of all blocks.
    """
    now = now or utcnow()
    net = ipaddress.IPv4Network(
        f"{network.network}/{network.cidr}", strict=False
    )
    first = int(net.network_address)
    size = net.num_addresses
    block_count = max(1, -(-size // BLOCK_SIZE))
    block = min(max(int(block), 0), block_count - 1)

    hosts = {int(ipaddress.IPv4Address(h.ip_address)): h for h in network.hosts}
    pools = _active_pools(network, net)
    # /31 and /32 have no separate network/broadcast address (RFC 3021).
    special = {}
    if net.prefixlen <= 30:
        special[first] = "Network address"
        special[int(net.broadcast_address)] = "Broadcast address"

    start = first + block * BLOCK_SIZE
    end = min(start + BLOCK_SIZE, first + size)
    cells = []
    counts = dict.fromkeys(CATEGORY_LABELS, 0)
    for value in range(start, end):
        host = hosts.get(value)
        if host is not None:
            category = host_category(host, now)
        elif value in special:
            category = CATEGORY_NETWORK
        elif _in_pools(value, pools):
            category = CATEGORY_POOL
        else:
            category = CATEGORY_FREE
        counts[category] += 1
        cells.append(
            {
                "ip": str(ipaddress.IPv4Address(value)),
                "category": category,
                "host": host,
                "state_label": (
                    allocation_label(derive_allocation_state(host, now))
                    if host is not None
                    else special.get(value, CATEGORY_LABELS[category])
                ),
            }
        )

    overview = None
    if 1 < block_count <= MAX_OVERVIEW_BLOCKS:
        overview = _block_overview(first, size, block_count, hosts, pools)

    return {
        "cells": cells,
        "counts": counts,
        "labels": CATEGORY_LABELS,
        "block": block,
        "block_count": block_count,
        "block_start": str(ipaddress.IPv4Address(start)),
        "block_end": str(ipaddress.IPv4Address(end - 1)),
        # Narrow screens use 16 columns, wide screens 32 (see template).
        "columns": min(16, len(cells)),
        "columns_wide": min(32, len(cells)),
        "overview": overview,
    }


def _block_overview(first, size, block_count, hosts, pools):
    """Return per-block occupancy without visiting every address.

    Occupied means a host record or an active DHCP pool address; hosts
    inside a pool are counted once.
    """
    used = [0] * block_count
    for value in hosts:
        used[(value - first) // BLOCK_SIZE] += 1
    for pool_start, pool_end in pools:
        for index in range(
            (pool_start - first) // BLOCK_SIZE,
            (pool_end - first) // BLOCK_SIZE + 1,
        ):
            block_start = first + index * BLOCK_SIZE
            block_end = block_start + BLOCK_SIZE - 1
            used[index] += (
                min(pool_end, block_end) - max(pool_start, block_start) + 1
            )
    for value in hosts:
        if _in_pools(value, pools):
            used[(value - first) // BLOCK_SIZE] -= 1

    blocks = []
    for index in range(block_count):
        block_size = min(BLOCK_SIZE, size - index * BLOCK_SIZE)
        blocks.append(
            {
                "index": index,
                "start": str(ipaddress.IPv4Address(first + index * BLOCK_SIZE)),
                "used": used[index],
                "size": block_size,
                "ratio": used[index] / block_size,
            }
        )
    return blocks
