"""Regression tests for the startup logging configuration (Step 6)."""
import json
import logging

import app.core.logging_config as lc


def test_resolve_level_reads_setting(monkeypatch):
    monkeypatch.setattr(lc.settings, "log_level", "WARNING", raising=False)
    assert lc.resolve_level() == logging.WARNING


def test_resolve_level_falls_back_on_garbage(monkeypatch):
    monkeypatch.setattr(lc.settings, "log_level", "not-a-level", raising=False)
    assert lc.resolve_level() == logging.INFO


def test_resolve_format(monkeypatch):
    monkeypatch.setenv("LOG_FORMAT", "json")
    assert lc.resolve_format() == "json"
    monkeypatch.setenv("LOG_FORMAT", "PLAIN")
    assert lc.resolve_format() == "plain"
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    assert lc.resolve_format() == "plain"


def test_json_formatter_emits_structured_fields():
    record = logging.LogRecord(
        "app.test", logging.INFO, __file__, 1, "hello %s", ("world",), None,
    )
    record.request_id = "abc-123"
    payload = json.loads(lc.JsonFormatter().format(record))
    assert payload["severity"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "abc-123"
    assert "timestamp" in payload


def test_configure_logging_is_idempotent(monkeypatch):
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    monkeypatch.setattr(lc, "_CONFIGURED", False, raising=False)
    monkeypatch.setattr(lc.settings, "log_level", "INFO", raising=False)
    try:
        root.handlers = []
        root.setLevel(logging.WARNING)
        lc.configure_logging()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        lc.configure_logging()  # second call must not stack another handler
        assert root.handlers == [handler]
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
