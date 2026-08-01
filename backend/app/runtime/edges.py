"""AutoFlow AI - Workflow runtime edges (generated from metadata).

Directed edges connect nodes. Optional condition labels let condition
nodes gate which downstream branch executes.
"""
import uuid
from typing import Optional


class Edge:
    """A directed connection between two nodes."""

    def __init__(self, source_id: str, target_id: str,
                 condition: Optional[str] = None,
                 label: str = "") -> None:
        self.edge_id = str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition  # e.g. "true", "false", or expression
        self.label = label or (condition or "")

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "condition": self.condition,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Edge":
        edge = cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            condition=data.get("condition"),
            label=data.get("label", ""),
        )
        edge.edge_id = data.get("edge_id", edge.edge_id)
        return edge

    def matches(self, result: bool) -> bool:
        """Return True when this edge's condition matches a branch result."""
        if not self.condition:
            return True
        cond = self.condition.strip().lower()
        if cond in ("true", "yes", "1"):
            return bool(result)
        if cond in ("false", "no", "0"):
            return not result
        return True  # non-boolean conditions are ignored by the runtime

    def __repr__(self) -> str:
        return f"Edge({self.source_id!r} -> {self.target_id!r})"
