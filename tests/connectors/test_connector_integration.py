"""AutoFlow AI - Connector framework integration tests (generated)."""

import asyncio
import json
import threading
import time
import unittest

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ActionNotFoundError, AuthenticationError, CircuitOpenError,
    ConnectorNotFoundError, DuplicateConnectorError, PermissionDeniedError,
    RateLimitError, TenantIsolationError, ValidationError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.loader import ConnectorLoader
from app.connectors.manager import ConnectorManager
from app.connectors.models import ActionRequest, ActionResponse, TriggerEvent
from app.connectors.registry import ConnectorRegistry
from app.connectors.serialization.validation import validate_inputs
from app.connectors.execution.rate_limit import RateLimiter
from app.connectors.execution.retry import CircuitBreaker, RetryStrategy
from app.connectors.security.credentials import CredentialStore
from app.connectors.security.secrets import SecretManager
from app.connectors.execution.webhooks import WebhookManager
from app.connectors.execution.polling import PollingRunner
from app.connectors.observability.metrics import ConnectorMetrics
from app.connectors.observability.tracing import ConnectorTracer


CONNECTOR_NAMES = ['Airtable', 'Confluence', 'Discord', 'Dropbox', 'GitHub', 'GitLab', 'Gmail', 'Google Drive', 'GraphQL', 'Jira', 'Linear', 'Microsoft Teams', 'MongoDB', 'MySQL', 'Notion', 'OneDrive', 'Outlook', 'PayPal', 'PostgreSQL', 'REST', 'Redis', 'Shopify', 'Slack', 'Stripe', 'Webhook', 'gRPC']
CONNECTOR_COUNT = 26


class _EchoConnector(BaseConnector):
    """In-memory connector used to exercise the SDK without I/O."""

    name = "echo"
    version = "1.0.0"
    metadata = {
        "actions": {
            "echo": {
                "description": "Echo inputs back", "kind": "run",
                "inputs": {"message": "string"},
                "outputs": {"echo": "string"},
                "required_permissions": [],
                "idempotent": True, "long_running": False,
                "streaming": False,
            },
            "fail": {
                "description": "Always fails", "kind": "run",
                "inputs": {}, "outputs": {},
                "required_permissions": [],
                "idempotent": False, "long_running": False,
                "streaming": False,
            },
        },
        "triggers": {
            "ping": {
                "description": "Produces an event", "kind": "manual",
                "webhook": False, "polling_interval_seconds": 0,
                "cron": "", "supported_events": ["echo.ping"],
            },
        },
        "rate_limits": {"default": "1000/minute", "rules": {}},
        "retry_policy": {"max_attempts": 2, "base_delay": 0.0,
                           "max_delay": 0.5, "backoff_factor": 1.0},
        "capabilities": {"actions": True, "triggers": True},
    }

    def execute_action(self, action, inputs, context=None):
        if action == "fail":
            raise RuntimeError("boom")
        return ActionResponse(ok=True, data=dict(inputs or {}),
                              connector=self.name, action=action)

    def poll(self, trigger, context=None):
        """Produce a repeatable event (stable id) to exercise dedup."""
        return [TriggerEvent(
            event_type="echo.ping", payload={"n": 1},
            connector=self.name, trigger=trigger,
            event_id="stable-event-1",
        )]


class TestConnectorSdk(unittest.TestCase):
    """SDK lifecycle contract tests."""

    def setUp(self):
        self.connector = _EchoConnector()

    def test_connect_disconnect(self):
        self.assertFalse(self.connector.is_connected)
        self.assertTrue(self.connector.connect())
        self.assertTrue(self.connector.is_connected)
        self.connector.disconnect()
        self.assertFalse(self.connector.is_connected)

    def test_authenticate_without_auth(self):
        result = self.connector.authenticate()
        self.assertEqual(result["method"], "none")

    def test_refresh_token_without_auth(self):
        self.assertIsNone(self.connector.refresh_token())

    def test_discover_returns_metadata(self):
        meta = self.connector.discover()
        self.assertEqual(meta["name"], "echo")
        self.assertIn("echo", meta["actions"])

    def test_validate_ok_and_missing_input(self):
        self.connector.validate("echo", {"message": "hi"})
        with self.assertRaises(ValidationError):
            self.connector.validate("echo", {})

    def test_validate_unknown_action(self):
        with self.assertRaises(ActionNotFoundError):
            self.connector.validate("nope", {})

    def test_execute_trigger_manual_returns_events(self):
        events = self.connector.execute_trigger("ping")
        self.assertIsInstance(events, list)

    def test_health_ok(self):
        result = self.connector.health()
        self.assertTrue(result.ok)

    def test_rollback_cleanup_noop(self):
        self.connector.rollback("echo", {}, ActionResponse(ok=True))
        self.connector.cleanup()

    def test_verify_webhook_signature(self):
        signed = self.connector.verify_webhook_signature(
            b"payload", "bad", "secret")
        self.assertFalse(signed)
        import hashlib
        import hmac
        expected = "sha256=" + hmac.new(
            b"secret", b"payload", hashlib.sha256).hexdigest()
        self.assertTrue(self.connector.verify_webhook_signature(
            b"payload", expected, "secret"))


class TestConnectorRegistry(unittest.TestCase):
    """Registry: registration, versioning, capability filtering."""

    def setUp(self):
        self.registry = ConnectorRegistry()
        self.registry.register(_EchoConnector)

    def test_register_and_get(self):
        self.assertTrue(self.registry.has("echo"))
        cls = self.registry.get("echo")
        self.assertEqual(cls, _EchoConnector)

    def test_duplicate_registration_raises(self):
        with self.assertRaises(DuplicateConnectorError):
            self.registry.register(_EchoConnector)

    def test_get_unknown_raises(self):
        with self.assertRaises(ConnectorNotFoundError):
            self.registry.get("nope")

    def test_names_and_count(self):
        self.assertEqual(self.registry.names(), ["echo"])
        self.assertEqual(self.registry.count(), 1)

    def test_by_capability(self):
        found = self.registry.by_capability("actions")
        self.assertIn(_EchoConnector, found)

    def test_unregister(self):
        self.assertTrue(self.registry.unregister("echo"))
        self.assertFalse(self.registry.has("echo"))


class TestMetadataConnectors(unittest.TestCase):
    """Every metadata-driven connector module is present and importable."""

    def test_all_connectors_importable(self):
        loader = ConnectorLoader()
        found = loader.discover()
        self.assertEqual(len(found), CONNECTOR_COUNT)
        for name in CONNECTOR_NAMES:
            self.assertIn(name, found)

    def test_each_connector_has_actions(self):
        loader = ConnectorLoader()
        found = loader.discover()
        for cls in found.values():
            self.assertTrue(cls.metadata.get("actions"),
                            f"{cls.name} has no actions")

    def test_each_connector_has_metadata_identity(self):
        loader = ConnectorLoader()
        found = loader.discover()
        for cls in found.values():
            self.assertTrue(cls.name)
            self.assertTrue(cls.version)


class TestConnectorFactory(unittest.TestCase):
    """Factory: by name, by version, by capability."""

    def setUp(self):
        self.factory = ConnectorFactory()
        self.factory.registry.register(_EchoConnector)

    def test_create_by_name(self):
        connector = self.factory.create("echo")
        self.assertEqual(connector.name, "echo")

    def test_create_by_version(self):
        connector = self.factory.create_by_version("echo", "1.0.0")
        self.assertEqual(connector.name, "echo")

    def test_create_by_capability(self):
        instances = self.factory.create_by_capability("actions")
        self.assertTrue(any(i.name == "echo" for i in instances))

    def test_create_unknown_raises(self):
        with self.assertRaises(ConnectorNotFoundError):
            self.factory.create("nope")


class TestConnectorManager(unittest.TestCase):
    """Manager: tenant-scoped lifecycle + actions."""

    def setUp(self):
        self.manager = ConnectorManager()
        self.manager.registry.register(_EchoConnector)

    def test_connect_and_list_instances(self):
        instance = self.manager.connect("echo", "org-1")
        self.assertEqual(instance.organization_id, "org-1")
        self.assertEqual(len(self.manager.list_instances("org-1")), 1)
        self.assertEqual(len(self.manager.list_instances("org-2")), 0)

    def test_execute_action(self):
        instance = self.manager.connect("echo", "org-1")
        response = self.manager.execute(ActionRequest(
            connector="echo", action="echo",
            instance_id=instance.instance_id,
            inputs={"message": "hi"},
            organization_id="org-1",
        ))
        self.assertTrue(response.ok)
        self.assertEqual(response.data["message"], "hi")

    def test_tenant_isolation_on_disconnect(self):
        instance = self.manager.connect("echo", "org-1")
        with self.assertRaises(TenantIsolationError):
            self.manager.disconnect(instance.instance_id, "org-2")

    def test_health(self):
        instance = self.manager.connect("echo", "org-1")
        result = self.manager.health(instance.instance_id, "org-1")
        self.assertTrue(result.ok)

    def test_run_trigger(self):
        self.manager.connect("echo", "org-1")
        events = self.manager.run_trigger("echo", "ping", "org-1")
        self.assertIsInstance(events, list)

    def test_disconnect_removes_instance(self):
        instance = self.manager.connect("echo", "org-1")
        self.manager.disconnect(instance.instance_id, "org-1")
        self.assertEqual(len(self.manager.list_instances("org-1")), 0)


class TestAuthentication(unittest.TestCase):
    """Auth strategies."""

    def test_jwt_sign_verify(self):
        from app.connectors.authentication.jwt import JWTStrategy
        strategy = JWTStrategy(credentials={"jwt_secret": "s3cret"})
        token = strategy.sign({"sub": "user-1"})
        payload = strategy.verify(token)
        self.assertEqual(payload["sub"], "user-1")

    def test_jwt_tamper_rejected(self):
        from app.connectors.authentication.jwt import JWTStrategy
        strategy = JWTStrategy(credentials={"jwt_secret": "s3cret"})
        token = strategy.sign({})
        with self.assertRaises(ValueError):
            strategy.verify(token[:-2] + "xx")

    def test_api_key_authenticate(self):
        from app.connectors.authentication.api_key import APIKeyStrategy
        strategy = APIKeyStrategy(credentials={"api_key": "k123"})
        result = strategy.authenticate()
        self.assertEqual(result["api_key"], "k123")

    def test_api_key_missing_raises(self):
        from app.connectors.authentication.api_key import APIKeyStrategy
        strategy = APIKeyStrategy()
        with self.assertRaises(ValueError):
            strategy.authenticate()

    def test_bearer_authenticate(self):
        from app.connectors.authentication.bearer import BearerStrategy
        strategy = BearerStrategy(credentials={"bearer_token": "tok"})
        result = strategy.authenticate()
        self.assertEqual(result["access_token"], "tok")

    def test_basic_authenticate(self):
        from app.connectors.authentication.basic import BasicAuthStrategy
        strategy = BasicAuthStrategy(
            credentials={"username": "u", "password": "p"})
        result = strategy.authenticate()
        self.assertIn("Basic ", result["Authorization"])

    def test_oauth_authorization_url(self):
        from app.connectors.authentication.oauth import OAuth2Strategy
        strategy = OAuth2Strategy(
            auth_config={
                "auth_url": "https://example.com/authorize",
                "supported_scopes": ["read"],
            },
            credentials={"client_id": "cid"},
        )
        url = strategy.get_authorization_url("https://app/cb")
        self.assertIn("client_id=cid", url)

    def test_oauth_authenticate_no_token(self):
        from app.connectors.authentication.oauth import OAuth2Strategy
        strategy = OAuth2Strategy()
        with self.assertRaises(ValueError):
            strategy.authenticate()


class TestExecution(unittest.TestCase):
    """Execution helpers: retry, circuit breaker, rate limit."""

    def test_retry_recovers(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("transient")
            return "ok"

        strategy = RetryStrategy(max_attempts=3, base_delay=0.0,
                                 max_delay=0.0, backoff_factor=1.0)
        self.assertEqual(strategy.run(flaky), "ok")
        self.assertEqual(strategy.last_attempts, 2)

    def test_retry_exhausted(self):
        def always_fails():
            raise ValueError("nope")
        strategy = RetryStrategy(max_attempts=2, base_delay=0.0,
                                 max_delay=0.0, backoff_factor=1.0)
        with self.assertRaises(Exception):
            strategy.run(always_fails)

    def test_circuit_breaker_opens(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30)
        self.assertTrue(breaker.allow())
        breaker.record_failure()
        breaker.record_failure()
        self.assertFalse(breaker.allow())
        breaker.record_success()
        self.assertTrue(breaker.allow())

    def test_rate_limiter_parses_limits(self):
        limiter = RateLimiter(default_limit="60/minute")
        self.assertAlmostEqual(limiter._bucket("x").rate, 1.0, places=3)

    def test_rate_limiter_blocks(self):
        limiter = RateLimiter(default_limit="1/second", enabled=True)
        self.assertTrue(limiter.try_acquire("a"))
        self.assertFalse(limiter.try_acquire("a"))

    def test_validate_inputs(self):
        errors = validate_inputs(
            {"name": "string", "count": "integer"},
            {"name": "x", "count": "bad"})
        self.assertTrue(any("count" in e for e in errors))


class TestSecurity(unittest.TestCase):
    """Security: secrets, credentials, permissions."""

    def test_secret_round_trip(self):
        manager = SecretManager(key="test-key")
        token = manager.encrypt("sk_live_123")
        self.assertEqual(manager.decrypt(token), "sk_live_123")

    def test_secret_mask(self):
        manager = SecretManager()
        masked = manager.mask("sk_12345678")
        self.assertTrue(masked.startswith("sk_1"))
        self.assertIn("*", masked)
        self.assertNotIn("5678", masked)

    def test_credential_store_round_trip(self):
        store = CredentialStore(secret_manager=SecretManager(key="k"))
        store.save("org-1", "stripe", {"secret_key": "sk_test"})
        creds = store.get("org-1", "stripe")
        self.assertEqual(creds["secret_key"], "sk_test")

    def test_credential_tenant_isolation(self):
        store = CredentialStore(secret_manager=SecretManager(key="k"))
        store.save("org-1", "stripe", {"secret_key": "a"})
        self.assertEqual(store.get("org-2", "stripe"), {})

    def test_permission_check(self):
        from app.connectors.security.permissions import PermissionValidator
        validator = PermissionValidator()
        with self.assertRaises(PermissionDeniedError):
            validator.check("stripe", "charge",
                            {"required_permissions": ["payment_intent"]},
                            granted_scopes=["customer"])


class TestObservability(unittest.TestCase):
    """Metrics + tracing."""

    def test_metrics_record_and_snapshot(self):
        metrics = ConnectorMetrics()
        metrics.record_action("stripe", "charge", True, 12.3)
        metrics.record_action("stripe", "charge", False, 4.5)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["actions_total"], 2)
        self.assertEqual(snapshot["action_failures"], 1)

    def test_tracer_spans(self):
        tracer = ConnectorTracer()
        span = tracer.start("charge")
        tracer.set_attribute(span, "action", "charge")
        tracer.end(span)
        spans = tracer.spans()
        self.assertEqual(len(spans), 1)
        self.assertIsNotNone(spans[0]["duration_ms"])


class TestWebhooksPolling(unittest.TestCase):
    """Webhook + polling helpers."""

    def test_webhook_signature_verify(self):
        manager = WebhookManager()
        import hashlib
        import hmac
        payload = b'{"a":1}'
        signature = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        self.assertTrue(manager.verify(payload, signature, "secret"))
        self.assertFalse(manager.verify(payload, "wrong", "secret"))

    def test_webhook_dispatch_requires_secret(self):
        manager = WebhookManager()
        received = []
        manager.register("order", lambda t, d: received.append(d), secret="s")
        manager.dispatch("order", b'{"id":1}', signature="bad")
        self.assertEqual(len(received), 0)

    def test_polling_dedup(self):
        runner = PollingRunner()
        events = []
        connector = _EchoConnector()

        def handler(event):
            events.append(event)

        first = runner.poll_once(connector, "ping", handler)
        self.assertEqual(first, 1)
        second = runner.poll_once(connector, "ping", handler)
        self.assertEqual(second, 0)  # duplicate suppressed
        self.assertEqual(len(events), 1)


class TestSerialization(unittest.TestCase):
    """Serializer helpers."""

    def test_serializer_dumps_loads(self):
        from app.connectors.serialization.serializer import ConnectorSerializer
        payload = {"a": 1, "nested": {"b": [1, 2]}}
        raw = ConnectorSerializer.dumps(payload)
        self.assertEqual(ConnectorSerializer.loads(raw), payload)

    def test_serializer_normalize_datetime(self):
        from datetime import datetime, timezone
        from app.connectors.serialization.serializer import ConnectorSerializer
        value = ConnectorSerializer.normalize(
            {"ts": datetime(2026, 1, 1, tzinfo=timezone.utc)})
        self.assertIsInstance(value["ts"], str)


if __name__ == "__main__":
    unittest.main()
