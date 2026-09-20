"""Structural tests for the production edge and network topology.

These assert the Step 4 hardening properties directly on the deployment
files, so a future edit that republishes a datastore port, drops the
internal network flag, or lets the trusted-proxy allowlist drift out of
sync fails CI instead of silently exposing PostgreSQL or Redis.

A tiny indentation-based reader is used instead of a YAML library so the
tests have no extra dependency and still inspect the raw declarations that
Docker Compose will act on.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.production.yml"
EDGE_HARNESS = ROOT / "docker-compose.edge-local-test.yml"
ENV_EXAMPLE = ROOT / ".env.example"
CADDYFILE = ROOT / "infra" / "docker" / "caddy" / "Caddyfile"
ROUTES = ROOT / "infra" / "docker" / "caddy" / "routes.caddy"

# Services that must never be reachable from the host.
PRIVATE_SERVICES = ("postgres", "redis", "backend", "frontend")

SUBNET_RE = re.compile(r"subnet:\s*\$\{EDGE_SUBNET:-([^}]+)\}")
TRUSTED_RE = re.compile(r"TRUSTED_PROXY_CIDRS:\s*\$\{TRUSTED_PROXY_CIDRS:-([^}]+)\}")


def _service_blocks(text):
    """Map each 2-space-indented key to its indented block."""
    blocks = {}
    current = None
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped.strip() or stripped.lstrip().startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            current = stripped.strip()[:-1]
            blocks[current] = []
        elif current is not None and line.startswith("    "):
            blocks[current].append(line)
    return {name: "\n".join(lines) for name, lines in blocks.items()}


@pytest.fixture(scope="module")
def compose_text():
    return COMPOSE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def services(compose_text):
    return _service_blocks(compose_text)


# --- Host port exposure ----------------------------------------------------


def test_only_the_edge_publishes_host_ports(services):
    """Caddy publishes 80/443; nothing else may publish anything."""
    caddy = services["caddy"]
    assert "ports:" in caddy
    assert "${HTTP_PORT:-80}:80" in caddy
    assert "${HTTPS_PORT:-443}:443" in caddy

    publishing = [name for name, block in services.items() if "ports:" in block]
    assert publishing == ["caddy"], f"unexpected host port publishers: {publishing}"


@pytest.mark.parametrize("name", PRIVATE_SERVICES)
def test_private_services_do_not_publish_ports(services, name):
    """PostgreSQL/Redis/backend/frontend are never bound to a host port."""
    block = services[name]
    assert "ports:" not in block, f"{name} must not publish host ports"
    # They are still reachable inside the compose network.
    assert "expose:" in block or name in ("postgres", "redis")


def test_datastores_are_not_published_by_the_local_harness_either():
    """The local edge harness must not re-publish datastore ports."""
    harness = _service_blocks(EDGE_HARNESS.read_text(encoding="utf-8"))
    for name in PRIVATE_SERVICES:
        if name in harness:
            assert "ports:" not in harness[name]


# --- Network segmentation --------------------------------------------------


@pytest.mark.parametrize("name", ("postgres", "redis"))
def test_datastores_only_join_the_internal_network(services, name):
    block = services[name]
    assert "- autoflow" in block
    assert "- edge" not in block, f"{name} must not join the public edge network"


def test_internal_network_has_no_route_off_host(services):
    assert "internal: true" in services["autoflow"]


def test_edge_subnet_is_pinned(compose_text):
    """The edge subnet must be deterministic so the trust list is exact."""
    match = SUBNET_RE.search(compose_text)
    assert match, "the edge network must pin a subnet"
    assert match.group(1) == "172.28.0.0/24"


def test_backend_trusts_only_the_edge_subnet(services, compose_text):
    """The trusted-proxy allowlist must match the pinned edge subnet."""
    subnet = SUBNET_RE.search(compose_text).group(1)
    trusted = TRUSTED_RE.search(compose_text).group(1)
    assert trusted == subnet
    # ...and it is delivered to the backend container.
    assert "TRUSTED_PROXY_CIDRS" in services["backend"]


def test_env_example_defaults_agree_with_compose(compose_text):
    """.env.example must not drift from the compose defaults."""
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    subnet = SUBNET_RE.search(compose_text).group(1)
    assert f"EDGE_SUBNET={subnet}" in env_text
    assert f"TRUSTED_PROXY_CIDRS={subnet}" in env_text


def test_backend_runs_proxy_aware(services):
    """uvicorn must be told a forwarded-allow-ips list (fail-closed default)."""
    block = services["backend"]
    assert "--proxy-headers" in block
    assert "--forwarded-allow-ips" in block


# --- Edge routing ----------------------------------------------------------


def test_caddyfile_imports_the_shared_routes():
    assert "import /etc/caddy/routes.caddy" in CADDYFILE.read_text(encoding="utf-8")


def test_caddyfile_defaults_to_localhost_site():
    assert "{$SITE_ADDRESS:localhost}" in CADDYFILE.read_text(encoding="utf-8")


def test_routes_proxy_api_and_frontend():
    routes = ROUTES.read_text(encoding="utf-8")
    assert "reverse_proxy backend:8000" in routes
    assert "reverse_proxy frontend:3000" in routes


def test_routes_disable_buffering_for_sse():
    """SSE streams must not be buffered, or events arrive only at the end."""
    assert "flush_interval -1" in ROUTES.read_text(encoding="utf-8")


def test_routes_forward_health_and_readiness():
    routes = ROUTES.read_text(encoding="utf-8")
    for path in ("/health", "/readiness", "/api/*"):
        assert path in routes
