"""AutoFlow AI - Compiler events/metrics tests (generated from metadata)."""

from app.compiler.compiler import PromptCompiler
from app.compiler.events import (
    emit_compile_completed, emit_compile_failed, emit_compile_started,
)
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import CompileOptions


def test_emit_events_noop():
    # Should not raise even when the bus is degraded/unavailable.
    emit_compile_started("w1")
    emit_compile_completed("w1", 1, 2, 1)
    emit_compile_failed("w1", "boom")


def test_metrics_initial():
    metrics = CompilationMetrics()
    data = metrics.to_dict()
    assert data["compile_count"] == 0
    assert data["failed_count"] == 0


def test_metrics_record():
    metrics = CompilationMetrics()
    metrics.record_stage("parse", 1.5)
    metrics.record_compile(3, 2, ok=True)
    data = metrics.to_dict()
    assert data["compile_count"] == 1
    assert data["total_nodes"] == 3
    assert "parse" in data["stage_times_ms"]


def test_compiler_metrics_after_compile():
    compiler = PromptCompiler(
        options=CompileOptions(emit_events=False, collect_metrics=True),
        connector_names=["slack"],
    )
    compiler.compile({
        "workflow": "w",
        "trigger": {"id": "trigger", "type": "event"},
        "steps": [{"id": "s1", "connector": "slack", "action": "post"}],
    })
    data = compiler.metrics_dict()
    assert data["compile_count"] == 1


def test_events_publish_to_bus():
    from app.events import subscribe, unsubscribe
    received = []

    def handler(event):
        received.append(event.event_type)

    unsubscribe("compiler.completed", handler)
    subscribe("compiler.completed", handler)
    try:
        emit_compile_completed("w", 1, 1, 0)
        assert "compiler.completed" in received
    finally:
        unsubscribe("compiler.completed", handler)
