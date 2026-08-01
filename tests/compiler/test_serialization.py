"""AutoFlow AI - Compiler serialization tests (generated from metadata)."""

from app.compiler.serializer import (
    export_schema, pretty_print, to_binary, to_json, to_yaml,
)
from app.compiler.deserializer import from_binary, from_json, from_yaml
from app.compiler.workflow_spec import WorkflowSpecification


def _make_spec():
    return WorkflowSpecification(
        workflow="w1",
        nodes=[{"id": "a", "type": "action", "name": "A"}],
        edges=[{"from": "trigger", "to": "a", "label": "starts"}],
    )


def test_to_json_roundtrip():
    raw = to_json(_make_spec())
    spec = from_json(raw)
    assert spec.workflow == "w1"
    assert spec.nodes[0]["id"] == "a"


def test_pretty_print():
    raw = pretty_print(_make_spec())
    assert "\n" in raw


def test_yaml_roundtrip():
    raw = to_yaml(_make_spec())
    spec = from_yaml(raw)
    assert spec.workflow == "w1"


def test_binary_roundtrip():
    raw = to_binary(_make_spec())
    spec = from_binary(raw)
    assert spec.workflow == "w1"


def test_export_schema():
    schema = export_schema()
    assert schema["title"] == "WorkflowSpecification"
    assert "nodes" in schema["properties"]
