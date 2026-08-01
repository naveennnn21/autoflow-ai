"""AutoFlow AI - Workflow specification tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import ValidationError, VersionError
from app.compiler.validator import WorkflowSpecificationValidator
from app.compiler.workflow_spec import WorkflowSpecification


def _make_spec(**overrides):
    spec = WorkflowSpecification(
        workflow="w1",
        trigger={"id": "trigger", "type": "event"},
        variables={"email": {"type": "string"}},
        nodes=[{
            "id": "a", "type": "action", "name": "A",
            "connector": "slack", "action": "post",
            "inputs": {"text": "{{ email }}"},
        }],
        edges=[{"from": "trigger", "to": "a", "label": "starts"}],
    )
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def test_validate_ok():
    validator = WorkflowSpecificationValidator(
        connector_names=["slack"],
        permissions={"post": ["member"]},
    )
    report = validator.validate(_make_spec())
    assert all(v == [] for v in report.values())


def test_validate_undefined_variable():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "{{ missing }}"}
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("missing" in e for e in report["variables"])


def test_validate_unused_variable():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "hello"}
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("never used" in e for e in report["variables"])


def test_validate_unknown_connector():
    spec = _make_spec()
    spec.nodes[0]["connector"] = "nonexistent"
    validator = WorkflowSpecificationValidator(connector_names=["slack"])
    report = validator.validate(spec)
    assert any("nonexistent" in e for e in report["connectors"])


def test_validate_runtime_compat():
    spec = _make_spec()
    spec.nodes[0]["type"] = "teleport"
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("runtime" in e for e in report["runtime_compat"])


def test_validate_or_raise():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "{{ missing }}"}
    with pytest.raises(ValidationError):
        WorkflowSpecificationValidator().validate_or_raise(spec)


def test_from_dict_unsupported_version():
    with pytest.raises(VersionError):
        WorkflowSpecification.from_dict({"workflow": "w", "version": 99})


def test_to_runtime_definition():
    spec = _make_spec()
    runtime = spec.to_runtime_definition()
    assert runtime["workflow_id"] == "w1"
    assert runtime["nodes"][0]["type"] == "action"
    assert runtime["nodes"][0]["subtype"] == "slack:post"
    assert runtime["edges"][0]["from"] == "trigger"
