"""Integration tests for the metadata-driven event bus.

Covers event registration from metadata, publish/subscribe/unsubscribe,
idempotency, versioning, persistence, replay, retry with backoff,
dead-lettering, and the generated metadata handler wiring.
"""
import importlib

import pytest

from app.events.base import DuplicateEventError, Event
from app.events.bus import (
    BUS_CONFIG, IDEMPOTENT_TYPES, EventBus, default_bus, publish, replay,
    reset_default_bus, retry, subscribe, unsubscribe,
)
from app.events.handlers.analytics import get_analytics_snapshot, reset_analytics
from app.events.handlers.audit import get_audit_events, reset_audit_events
from app.events.handlers.connector import get_connector_events, reset_connector_events
from app.events.handlers.notification import get_notifications, reset_notifications
from app.events.handlers.webhook import get_pending_deliveries, reset_webhook_events
from app.events.handlers.workflow import (
    get_retry_suggestions, get_workflow_events, reset_workflow_events,
)
from app.events.publisher import Publisher
from app.events.registry import METADATA_SUBSCRIPTIONS
from app.events.serializer import EventSerializer
from app.events.subscriber import subscriber
from app.events.tracing import tracer

# Expected metadata values embedded by the generator
EXPECTED_EVENT_TYPES = ['ai.workflow_generated', 'ai.workflow_optimized', 'connector.connected', 'connector.disconnected', 'connector.error', 'execution.retried', 'invoice.paid', 'notification.failed', 'notification.sent', 'organization.created', 'organization.deleted', 'organization.updated', 'subscription.cancelled', 'system.error', 'system.health_ok', 'user.created', 'user.deleted', 'user.updated', 'workflow.completed', 'workflow.failed', 'workflow.started']
EXPECTED_HANDLER_MAP = {'workflow.started': ['analytics', 'audit'], 'workflow.completed': ['analytics', 'notification'], 'workflow.failed': ['workflow', 'notification', 'analytics', 'audit'], 'execution.retried': ['workflow', 'audit'], 'user.created': ['analytics', 'audit'], 'user.updated': ['analytics', 'audit'], 'user.deleted': ['audit'], 'organization.created': ['analytics', 'audit'], 'organization.updated': ['analytics', 'audit'], 'organization.deleted': ['audit'], 'notification.sent': ['notification', 'analytics'], 'notification.failed': ['notification', 'analytics'], 'system.health_ok': ['analytics'], 'system.error': ['notification', 'webhook', 'analytics'], 'invoice.paid': ['notification', 'analytics', 'audit'], 'subscription.cancelled': ['notification', 'audit'], 'connector.connected': ['connector', 'analytics'], 'connector.disconnected': ['connector', 'analytics'], 'connector.error': ['connector', 'notification', 'webhook'], 'ai.workflow_generated': ['analytics', 'audit'], 'ai.workflow_optimized': ['analytics', 'audit']}
EXPECTED_IDEMPOTENT_TYPES = ['invoice.paid', 'organization.created', 'user.created', 'workflow.started']
EXPECTED_BUS_CONFIG = {'serializer': 'json', 'persistence': {'enabled': True, 'max_events': 10000, 'storage': 'memory'}, 'retry': {'enabled': True, 'max_attempts': 3, 'base_delay': 0.5, 'max_delay': 10.0, 'backoff_factor': 2.0}, 'dead_letter': {'enabled': True, 'max_retries': 5}, 'versioning': {'enabled': True}}


@pytest.fixture(autouse=True)
def reset_state():
    """Reset shared handler state and the default bus between tests."""
    reset_default_bus()
    reset_audit_events()
    reset_analytics()
    reset_notifications()
    reset_connector_events()
    reset_webhook_events()
    reset_workflow_events()
    tracer.enabled = True
    tracer.clear()
    yield
    reset_default_bus()
    reset_audit_events()
    reset_analytics()
    reset_notifications()
    reset_connector_events()
    reset_webhook_events()
    reset_workflow_events()
    tracer.enabled = True
    tracer.clear()


def make_bus(**overrides) -> EventBus:
    """Build an isolated bus with a small retry delay for fast tests."""
    config = {"retry": {"base_delay": 0.0, "max_delay": 0.0, "max_attempts": 2}}
    config.update(overrides)
    return EventBus(config=config)


class TestMetadataRegistration:
    """Events, handlers, and bus config registered from metadata."""

    def test_event_catalog_registered(self):
        """Every metadata event type is reflected in the generated registry."""
        assert set(METADATA_SUBSCRIPTIONS) == set(EXPECTED_EVENT_TYPES)

    def test_handler_map_matches_metadata(self):
        """Generated handler map matches the metadata handler assignments."""
        assert METADATA_SUBSCRIPTIONS == EXPECTED_HANDLER_MAP

    def test_bus_config_matches_metadata(self):
        """Generated bus config matches the metadata bus section."""
        assert BUS_CONFIG == EXPECTED_BUS_CONFIG

    def test_idempotent_types_registered(self):
        """Idempotent metadata events are enforced by the bus."""
        assert set(IDEMPOTENT_TYPES) == set(EXPECTED_IDEMPOTENT_TYPES)
        assert "workflow.started" in IDEMPOTENT_TYPES

    def test_metadata_handlers_importable(self):
        """Every declared handler module imports and exposes handle()."""
        for name in sorted({h for hs in EXPECTED_HANDLER_MAP.values() for h in hs}):
            module = importlib.import_module(f"app.events.handlers.{name}")
            assert callable(getattr(module, "handle", None))

    def test_default_bus_registers_metadata_handlers(self):
        """Constructing a bus subscribes the metadata-declared handlers."""
        bus = EventBus(config={"retry": {"base_delay": 0.0, "max_delay": 0.0}})
        expected = sum(len(hs) for hs in EXPECTED_HANDLER_MAP.values())
        assert bus.registry.count() >= expected


class TestPublishSubscribe:
    """publish()/subscribe()/unsubscribe() round trips."""

    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscriber(self):
        bus = make_bus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test.published", handler)
        event = Event(event_type="test.published", payload={"n": 1})
        await bus.publish(event)
        assert received == [event]
        assert bus.store.get(event.event_id).status == "delivered"

    @pytest.mark.asyncio
    async def test_sync_subscriber_supported(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.sync", lambda e: received.append(e.event_type))
        await bus.publish(Event(event_type="test.sync"))
        assert received == ["test.sync"]

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(self):
        bus = make_bus()
        received = []

        async def handler(event):
            received.append(event.event_id)

        bus.subscribe("test.unsub", handler)
        await bus.publish(Event(event_type="test.unsub"))
        assert bus.unsubscribe("test.unsub", handler) is True
        await bus.publish(Event(event_type="test.unsub"))
        assert bus.unsubscribe("test.unsub", handler) is False
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_wildcard_subscriber(self):
        bus = make_bus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        await bus.publish(Event(event_type="test.a"))
        await bus.publish(Event(event_type="test.b"))
        assert received == ["test.a", "test.b"]

    @pytest.mark.asyncio
    async def test_module_level_publish_subscribe(self):
        received = []

        async def handler(event):
            received.append(event.event_type)

        subscribe("test.module", handler)
        await publish(Event(event_type="test.module"))
        assert received == ["test.module"]
        assert unsubscribe("test.module", handler) is True

    @pytest.mark.asyncio
    async def test_subscriber_decorator(self):
        """The @subscriber decorator registers on the given (or default) bus."""
        bus = make_bus()
        received = []

        @subscriber("test.decorated", bus=bus)
        async def on_event(event):
            received.append(event.event_type)

        await bus.publish(Event(event_type="test.decorated"))
        assert received == ["test.decorated"]

    @pytest.mark.asyncio
    async def test_publisher_facade(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.facade", lambda e: received.append(e))
        pub = Publisher(bus=bus)
        event = await pub.emit("test.facade", {"k": "v"}, entity_id="e-1")
        assert received == [event]
        assert event.entity_id == "e-1"

    def test_serializer_round_trip(self):
        event = Event(
            event_type="test.serialized", version=2,
            payload={"a": 1}, entity_id="e-1",
        )
        raw = EventSerializer.serialize(event)
        restored = EventSerializer.deserialize(raw)
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.version == event.version
        assert restored.payload == {"a": 1}
        assert restored.entity_id == "e-1"


class TestIdempotencyVersioning:
    """Idempotency keys and event versioning."""

    @pytest.mark.asyncio
    async def test_idempotent_event_gets_key_and_rejects_duplicate(self):
        bus = make_bus()
        event = Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1"},
        )
        await bus.publish(event)
        assert event.idempotency_key  # auto-assigned from metadata

        duplicate = Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1"},
        )
        with pytest.raises(DuplicateEventError):
            await bus.publish(duplicate)

    @pytest.mark.asyncio
    async def test_non_idempotent_event_has_no_key(self):
        bus = make_bus()
        event = Event(event_type="test.plain", payload={})
        await bus.publish(event)
        assert event.idempotency_key is None

    @pytest.mark.asyncio
    async def test_versioning_preserved(self):
        bus = make_bus()
        event = Event(event_type="test.ver", version=3, payload={})
        await bus.publish(event)
        assert bus.store.get(event.event_id).event.version == 3



class TestPersistenceReplay:
    """Event persistence and replay."""

    @pytest.mark.asyncio
    async def test_events_persisted(self):
        bus = make_bus()
        await bus.publish(Event(event_type="test.persist"))
        await bus.publish(Event(event_type="test.persist"))
        assert bus.stored_count() == 2

    @pytest.mark.asyncio
    async def test_replay_redelivers_persisted_events(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.replay", lambda e: received.append(e.event_id))
        await bus.publish(Event(event_type="test.replay"))
        await bus.publish(Event(event_type="test.replay"))
        first = len(received)
        count = await bus.replay(event_type="test.replay")
        assert count == 2
        assert len(received) == first + 2

    @pytest.mark.asyncio
    async def test_module_level_replay(self):
        received = []

        async def handler(event):
            received.append(event.event_type)

        subscribe("test.replay.module", handler)
        await publish(Event(event_type="test.replay.module"))
        count = await replay(event_type="test.replay.module")
        assert count == 1
        assert received == ["test.replay.module", "test.replay.module"]


class TestRetryDeadLetter:
    """Retry with backoff and dead-letter support."""

    @pytest.mark.asyncio
    async def test_retry_recovers_transient_failure(self):
        bus = make_bus()
        attempts = {"n": 0}

        async def flaky(event):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("transient")

        bus.subscribe("test.retry", flaky)
        await bus.publish(Event(event_type="test.retry"))
        assert attempts["n"] == 2
        snap = bus.metrics.snapshot()
        assert snap["delivered"] == 1
        assert snap["retried"] == 1
        assert bus.dead_lettered_count() == 0

    @pytest.mark.asyncio
    async def test_exhausted_retries_dead_letter(self):
        bus = make_bus()  # max_attempts=2, zero delay

        async def broken(event):
            raise ValueError("kaboom")

        bus.subscribe("test.dl", broken)
        event = Event(event_type="test.dl")
        await bus.publish(event)
        assert bus.dead_lettered_count() == 1
        snap = bus.metrics.snapshot()
        assert snap["failed"] == 1
        assert snap["dead_lettered"] == 1
        assert bus.store.get(event.event_id).status == "dead_lettered"

    @pytest.mark.asyncio
    async def test_manual_retry_of_dead_lettered_event(self):
        bus = make_bus()

        async def broken(event):
            raise ValueError("kaboom")

        bus.subscribe("test.retry.dl", broken)
        event = await bus.publish(Event(event_type="test.retry.dl"))
        assert bus.dead_lettered_count() == 1

        bus.unsubscribe("test.retry.dl", broken)
        received = []
        bus.subscribe("test.retry.dl", lambda e: received.append(e.event_id))

        assert await bus.retry(event.event_id) is True
        assert received == [event.event_id]
        assert bus.dead_lettered_count() == 0
        assert bus.store.get(event.event_id).status == "delivered"

    @pytest.mark.asyncio
    async def test_retry_missing_event_returns_false(self):
        bus = make_bus()
        assert await bus.retry("does-not-exist") is False


class TestMetadataHandlers:
    """Generated handler modules consume metadata events."""

    @pytest.mark.asyncio
    async def test_audit_handler_records_events(self):
        await publish(Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1", "execution_id": "ex-1"},
        ))
        events = get_audit_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "workflow.started"

    @pytest.mark.asyncio
    async def test_analytics_handler_counts_events(self):
        await publish(Event(event_type="workflow.completed"))
        await publish(Event(event_type="workflow.completed"))
        snap = get_analytics_snapshot()
        assert snap["by_type"]["workflow.completed"] == 2

    @pytest.mark.asyncio
    async def test_notification_handler_queues(self):
        await publish(Event(event_type="invoice.paid", payload={"amount": 100}))
        notifications = get_notifications()
        assert len(notifications) == 1
        assert notifications[0]["event_type"] == "invoice.paid"

    @pytest.mark.asyncio
    async def test_connector_handler_tracks_state(self):
        await publish(Event(event_type="connector.connected", entity_id="conn-1"))
        await publish(Event(event_type="connector.error", entity_id="conn-1"))
        assert len(get_connector_events()) == 2

    @pytest.mark.asyncio
    async def test_workflow_handler_suggests_retries(self):
        await publish(Event(
            event_type="workflow.failed",
            payload={"workflow_id": "wf-1", "execution_id": "ex-1", "error": "boom"},
        ))
        assert len(get_workflow_events()) == 1
        assert len(get_retry_suggestions()) == 1

    @pytest.mark.asyncio
    async def test_webhook_handler_queues_deliveries(self):
        await publish(Event(
            event_type="connector.error", entity_id="conn-1", payload={"msg": "x"},
        ))
        assert len(get_pending_deliveries()) == 1


class TestHandlerPriority:
    """Handlers execute in descending priority order."""

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.prio", lambda e: order.append("low"), priority=0)
        bus.subscribe("test.prio", lambda e: order.append("high"), priority=10)
        bus.subscribe("test.prio", lambda e: order.append("mid"), priority=5)
        await bus.publish(Event(event_type="test.prio"))
        assert order == ["high", "mid", "low"]

    @pytest.mark.asyncio
    async def test_equal_priority_is_stable(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.stable", lambda e: order.append(1))
        bus.subscribe("test.stable", lambda e: order.append(2))
        await bus.publish(Event(event_type="test.stable"))
        assert order == [1, 2]

    @pytest.mark.asyncio
    async def test_wildcard_and_exact_priority(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.wild", lambda e: order.append("wild"), priority=0)
        bus.subscribe("test.wild", lambda e: order.append("exact"), priority=1)
        await bus.publish(Event(event_type="test.wild"))
        assert order == ["exact", "wild"]

    @pytest.mark.asyncio
    async def test_module_level_priority(self):
        received = []
        subscribe("test.mod.prio", lambda e: received.append("a"), priority=1)
        subscribe("test.mod.prio", lambda e: received.append("b"), priority=2)
        await publish(Event(event_type="test.mod.prio"))
        assert received == ["b", "a"]

    @pytest.mark.asyncio
    async def test_subscriber_decorator_priority(self):
        bus = make_bus()
        received = []

        @subscriber("test.dec.prio", bus=bus, priority=3)
        async def low(event):
            received.append("low")

        @subscriber("test.dec.prio", bus=bus, priority=9)
        async def high(event):
            received.append("high")

        await bus.publish(Event(event_type="test.dec.prio"))
        assert received == ["high", "low"]


class TestRequestMetadata:
    """Request ids, correlation ids, and the metadata bag."""

    @pytest.mark.asyncio
    async def test_request_id_auto_assigned(self):
        bus = make_bus()
        event = await bus.publish(Event(event_type="test.reqid"))
        assert event.request_id
        assert event.correlation_id == event.request_id

    @pytest.mark.asyncio
    async def test_request_id_propagated(self):
        bus = make_bus()
        event = await bus.publish(Event(
            event_type="test.reqid.prop",
            request_id="req-abc",
            correlation_id="corr-xyz",
        ))
        assert event.request_id == "req-abc"
        assert event.correlation_id == "corr-xyz"
        persisted = bus.store.get(event.event_id)
        assert persisted.event.request_id == "req-abc"

    @pytest.mark.asyncio
    async def test_metadata_bag_preserved(self):
        bus = make_bus()
        event = await bus.publish(Event(
            event_type="test.meta",
            metadata={"source": "unit", "priority": "high"},
        ))
        assert event.metadata == {"source": "unit", "priority": "high"}
        assert bus.store.get(event.event_id).event.metadata["source"] == "unit"

    @pytest.mark.asyncio
    async def test_publisher_request_id(self):
        bus = make_bus()
        pub = Publisher(bus=bus)
        event = pub.new_event("test.pub.reqid", request_id="req-from-pub")
        await bus.publish(event)
        assert event.request_id == "req-from-pub"


class TestTracingMetrics:
    """Trace spans and metric counters."""

    @pytest.mark.asyncio
    async def test_trace_records_spans(self):
        bus = make_bus()

        async def handler(event):
            pass

        bus.subscribe("test.trace", handler)
        event = await bus.publish(Event(event_type="test.trace"))
        traces = tracer.list()
        assert len(traces) == 1
        trace = traces[0]
        assert trace["event_id"] == event.event_id
        assert trace["event_type"] == "test.trace"
        assert trace["outcome"] == "delivered"
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["ok"] is True
        assert trace["spans"][0]["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_trace_records_failure(self):
        bus = make_bus()

        async def broken(event):
            raise ValueError("trace-boom")

        bus.subscribe("test.trace.fail", broken)
        event = await bus.publish(Event(event_type="test.trace.fail"))
        traces = tracer.list()
        assert len(traces) == 1
        assert traces[0]["outcome"] == "dead_lettered"
        assert traces[0]["spans"][0]["ok"] is False
        assert "trace-boom" in traces[0]["spans"][0]["error"]

    @pytest.mark.asyncio
    async def test_tracer_disable_and_clear(self):
        bus = make_bus()
        tracer.enabled = False
        await bus.publish(Event(event_type="test.trace.off"))
        tracer.enabled = True
        assert tracer.count() == 0
        tracer.clear()
        assert tracer.count() == 0

    def test_metrics_snapshot_keys(self):
        bus = make_bus()
        snap = bus.snapshot()
        for key in ("published", "delivered", "failed", "retried",
                    "dead_lettered", "replayed", "by_type", "stored",
                    "subscribers"):
            assert key in snap

    @pytest.mark.asyncio
    async def test_metrics_by_type(self):
        bus = make_bus()
        await bus.publish(Event(event_type="test.metric"))
        snap = bus.snapshot()
        assert snap["published"] == 1
        assert snap["by_type"]["test.metric"] == 1

