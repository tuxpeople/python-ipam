"""Shared normalization helpers for network addresses and hostnames.

Used by both the CSV/JSON importers (web upload) and the REST API so
that data entering IPAM through either path is normalized the same
way.
"""

import ipaddress


def normalize_network_address(network, cidr):
    """Return the canonical network address for a network/cidr pair.

    Accepts any host IP within the network, not just its base address:
    ``normalize_network_address("10.20.1.42", 24) == "10.20.1.0"``.
    """
    net = ipaddress.IPv4Network(f"{network}/{cidr}", strict=False)
    return str(net.network_address)


def strip_domain_suffix(hostname, domain):
    """Remove a trailing domain suffix from a hostname, if present.

    Matching is case-insensitive and tolerates a trailing DNS dot on
    either the hostname or the domain. Only a complete suffix
    (including its separating dot) is removed; a hostname equal to the
    domain, or with no matching suffix, is returned unchanged.
    """
    if not hostname or not domain:
        return hostname
    domain = domain.strip().removesuffix(".")
    if not domain:
        return hostname
    name = hostname.removesuffix(".")
    suffix = f".{domain}"
    if len(name) > len(suffix) and name.lower().endswith(suffix.lower()):
        return name[: -len(suffix)]
    return hostname
