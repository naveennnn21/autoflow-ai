"""AutoFlow AI - trusted-proxy aware client address resolution.

In production the API runs behind the Caddy edge (see
``infra/docker/caddy/``), so every request arrives from the proxy address.
``request.client.host`` is therefore the *proxy* for all clients, which
would make rate limiting useless (one shared bucket for the whole world)
and audit trails wrong.

The real client is carried in ``X-Forwarded-For`` - but that header is
client-controlled and trivially spoofable. It may only be believed when
the direct peer is a proxy we explicitly trust, configured through
``TRUSTED_PROXY_CIDRS``. With that list empty (the default) forwarded
headers are ignored entirely and the peer address is used, so the
behaviour is fail-closed.
"""
from __future__ import annotations

import ipaddress
from typing import Iterable, List, Optional, Union

from starlette.requests import Request

#: Header carrying the proxy chain, left-most entry is the original client.
XFF_HEADER = "x-forwarded-for"

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def parse_trusted_proxies(
    raw: Optional[Union[str, Iterable[str]]],
) -> List[Network]:
    """Parse a CIDR/IP list into networks.

    Accepts a comma-separated string (the ``TRUSTED_PROXY_CIDRS`` env
    format) or any iterable of strings. Invalid entries are skipped rather
    than raising, so a typo can never crash request handling; an empty or
    unset value yields ``[]`` (trust nobody).
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        items = raw.split(",")
    else:
        items = [str(item) for item in raw]

    networks: List[Network] = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return networks


def _as_address(host: str) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """Parse a host into an ip address, unwrapping IPv4-mapped IPv6."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def is_trusted_proxy(host: str, networks: Iterable[Network]) -> bool:
    """Return True when *host* falls inside one of the trusted networks."""
    address = _as_address(host)
    if address is None:
        return False
    for network in networks:
        try:
            if address in network:
                return True
        except TypeError:
            # IPv4 address against an IPv6 network (or vice versa).
            continue
    return False


def resolve_client_ip(
    request: Request,
    trusted_proxies: Optional[Iterable[Network]] = None,
) -> str:
    """Return the best-known client address for *request*.

    Falls back to the direct peer (``request.client.host``) whenever
    forwarded headers cannot be trusted:
      * no trusted proxy ranges are configured, or
      * the direct peer is not inside them.

    Otherwise the ``X-Forwarded-For`` chain is walked right-to-left,
    skipping hops that are themselves trusted proxies, and the first
    untrusted address - the real client - is returned.
    """
    peer = request.client.host if request.client else ""
    networks = list(trusted_proxies or [])

    if not networks or not is_trusted_proxy(peer, networks):
        # Untrusted (or unconfigured) peer: never believe X-Forwarded-For.
        return peer or "unknown"

    forwarded = request.headers.get(XFF_HEADER, "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]

    for candidate in reversed(chain):
        if is_trusted_proxy(candidate, networks):
            continue
        return candidate

    # Every hop was a trusted proxy (or the chain was empty): the peer is
    # the most specific address we can vouch for.
    return peer or "unknown"
