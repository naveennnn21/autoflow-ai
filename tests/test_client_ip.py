"""Unit tests for trusted-proxy aware client address resolution.

These cover the security-critical property behind the Caddy edge: the
forwarded header is believed only for peers inside TRUSTED_PROXY_CIDRS, so
an untrusted client can neither spoof its rate-limit identity nor forge an
audit address.
"""
import ipaddress

from starlette.requests import Request

from app.core.client_ip import (
    is_trusted_proxy,
    parse_trusted_proxies,
    resolve_client_ip,
)


def make_request(peer="127.0.0.1", xff=None):
    """Build a minimal ASGI request with an optional X-Forwarded-For."""
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode("latin1")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "server": ("test", 80),
        "client": (peer, 12345) if peer else None,
    }
    return Request(scope)


# --- parse_trusted_proxies -------------------------------------------------


def test_parse_handles_unset_and_empty_values():
    assert parse_trusted_proxies(None) == []
    assert parse_trusted_proxies("") == []
    assert parse_trusted_proxies("   ") == []
    assert parse_trusted_proxies([]) == []


def test_parse_accepts_comma_separated_cidrs():
    networks = parse_trusted_proxies("172.28.0.0/24, 10.0.0.0/8")
    assert len(networks) == 2
    assert ipaddress.ip_network("172.28.0.0/24") in networks


def test_parse_accepts_bare_ip_as_single_host():
    networks = parse_trusted_proxies("203.0.113.7")
    assert networks == [ipaddress.ip_network("203.0.113.7/32")]


def test_parse_skips_invalid_entries_without_raising():
    networks = parse_trusted_proxies("not-an-ip, 172.28.0.0/24, 999.1.1.1/8")
    assert networks == [ipaddress.ip_network("172.28.0.0/24")]


# --- is_trusted_proxy ------------------------------------------------------


def test_is_trusted_proxy_matches_inside_range():
    networks = parse_trusted_proxies("172.28.0.0/24")
    assert is_trusted_proxy("172.28.0.5", networks) is True
    assert is_trusted_proxy("203.0.113.5", networks) is False


def test_is_trusted_proxy_handles_ipv4_mapped_ipv6():
    networks = parse_trusted_proxies("172.28.0.0/24")
    assert is_trusted_proxy("::ffff:172.28.0.5", networks) is True


def test_is_trusted_proxy_rejects_garbage_and_cross_family():
    networks = parse_trusted_proxies("10.0.0.0/8")
    assert is_trusted_proxy("not-an-ip", networks) is False
    assert is_trusted_proxy("2001:db8::1", networks) is False


# --- resolve_client_ip -----------------------------------------------------


def test_no_trusted_proxies_uses_peer_and_ignores_header():
    request = make_request(peer="203.0.113.9", xff="10.1.1.1")
    assert resolve_client_ip(request, []) == "203.0.113.9"


def test_untrusted_peer_cannot_spoof_forwarded_address():
    networks = parse_trusted_proxies("10.0.0.0/8")
    request = make_request(peer="203.0.113.9", xff="198.51.100.7")
    assert resolve_client_ip(request, networks) == "203.0.113.9"


def test_trusted_peer_supplies_forwarded_client():
    networks = parse_trusted_proxies("172.28.0.0/24")
    request = make_request(peer="172.28.0.5", xff="203.0.113.9")
    assert resolve_client_ip(request, networks) == "203.0.113.9"


def test_trusted_chain_is_walked_from_the_right():
    networks = parse_trusted_proxies("172.28.0.0/24")
    request = make_request(peer="172.28.0.5", xff="203.0.113.9, 172.28.0.6")
    assert resolve_client_ip(request, networks) == "203.0.113.9"


def test_client_injected_entry_is_ignored():
    """A client may prepend entries; the right-most untrusted hop still wins."""
    networks = parse_trusted_proxies("172.28.0.0/24")
    request = make_request(peer="172.28.0.5", xff="1.2.3.4, 203.0.113.9")
    assert resolve_client_ip(request, networks) == "203.0.113.9"


def test_all_hops_trusted_falls_back_to_peer():
    networks = parse_trusted_proxies("172.28.0.0/24")
    request = make_request(peer="172.28.0.5", xff="172.28.0.6")
    assert resolve_client_ip(request, networks) == "172.28.0.5"


def test_missing_header_and_missing_client_are_safe():
    networks = parse_trusted_proxies("172.28.0.0/24")
    assert resolve_client_ip(make_request(peer="172.28.0.5"), networks) == "172.28.0.5"
    assert resolve_client_ip(make_request(peer=None), networks) == "unknown"
    assert resolve_client_ip(make_request(peer=None), []) == "unknown"
