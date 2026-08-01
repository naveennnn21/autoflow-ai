"""AutoFlow AI - Workflow runtime nodes (generated from metadata).

Node model for workflow graphs: typed nodes with configuration, plus
the result object produced by executing a node.
"""
from typing import Dict, Optional


class NodeType:
    """Well-known node type families and subtypes."""

    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    TRANSFORM = "transform"
    NOTIFICATION = "notification"
    WAIT = "wait"

    TRIGGERS = ("schedule", "form_submission", "event")
    ACTIONS = ("api_call", "transform", "database_write", "execute",
               "send_email", "send_slack", "send_push", "notification",
               "wait_for_approval")
    CONDITIONS = ("approved", "check_preferences")

    @classmethod
    def family(cls, node_type: str) -> str:
        """Return the family of a node type (possibly the type itself)."""
        if node_type in cls.TRIGGERS:
            return cls.TRIGGER
        if node_type in cls.ACTIONS:
            return cls.ACTION
        if node_type in cls.CONDITIONS:
            return cls.CONDITION
        return node_type  # already a family name


class Node:
    """A single node in a workflow graph."""

    def __init__(self, node_id: str, node_type: str, name: str = "",
                 config: Optional[dict] = None,
                 position: Optional[dict] = None) -> None:
        self.node_id = node_id
        self.node_type = node_type
        self.name = name or node_id
        self.config = dict(config or {})
        self.position = dict(position or {})

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "config": dict(self.config),
            "position": dict(self.position),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        return cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            name=data.get("name", ""),
            config=data.get("config", {}),
            position=data.get("position", {}),
        )

    def __repr__(self) -> str:
        return f"Node({self.node_id!r}, {self.node_type!r})"


class NodeResult:
    """Outcome of executing a node."""

    def __init__(self, node_id: str, status: str = "success",
                 output: Optional[dict] = None,
                 error: Optional[str] = None,
                 attempts: int = 1, duration_ms: float = 0.0) -> None:
        self.node_id = node_id
        self.status = status  # success | failure | skipped
        self.output = dict(output or {})
        self.error = error
        self.attempts = attempts
        self.duration_ms = duration_ms

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "output": dict(self.output),
            "error": self.error,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NodeResult":
        return cls(
            node_id=data["node_id"],
            status=data.get("status", "success"),
            output=data.get("output", {}),
            error=data.get("error"),
            attempts=data.get("attempts", 1),
            duration_ms=data.get("duration_ms", 0.0),
        )

    def __repr__(self) -> str:
        return f"NodeResult({self.node_id!r}, {self.status!r})"
