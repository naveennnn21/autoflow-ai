"""AutoFlow AI - Execution rollback (generated from metadata).

Compensation-based rollback: when an execution fails, completed nodes
are compensated in reverse dependency order using registered
compensation handlers.
"""
import logging
from typing import Callable, Dict, List

from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node
from app.runtime.state import ExecutionState

logger = logging.getLogger(__name__)


class RollbackManager:
    """Coordinates compensation of completed nodes on failure."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._compensators: Dict[str, Callable[[Node, ExecutionState], None]] = {}

    def register_compensation(self, node_type: str,
                              func: Callable[[Node, ExecutionState], None]) -> None:
        self._compensators[node_type] = func

    def compensate(self, state: ExecutionState,
                   graph: WorkflowGraph) -> List[str]:
        """Compensate completed nodes in reverse topological order.

        Returns the list of compensated node ids (empty when disabled).
        """
        if not self.enabled:
            return []
        try:
            order = graph.topological_sort()
        except Exception:  # noqa: BLE001 - never block rollback
            order = list(state.node_states.keys())
        completed = [
            nid for nid in reversed(order)
            if state.node_states.get(nid) == "completed"
        ]
        compensated: List[str] = []
        for nid in completed:
            node = graph.node(nid)
            func = self._compensators.get(node.node_type)
            try:
                if func is not None:
                    func(node, state)
                compensated.append(nid)
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.warning("compensation failed for %s: %s", nid, exc)
        return compensated

    def reset(self) -> None:
        self._compensators.clear()
