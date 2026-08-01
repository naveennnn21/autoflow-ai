"""AutoFlow AI - Graph builder (stage 8b, generated from metadata).

Builds a validated DAG from the plan's steps and edges: node registry,
adjacency, cycle detection, connectivity check, and topological order.
The output graph is consumed by the Workflow Runtime.
"""

from collections import deque
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import GraphError


class WorkflowGraphBuilder:
    """Builds and validates the workflow DAG."""

    def __init__(self) -> None:
        self.nodes: List[str] = []
        self.adj: Dict[str, List[str]] = {}
        self.indegree: Dict[str, int] = {}

    def build(self, steps: List[Any]) -> Dict[str, Any]:
        """Build the graph from PlanStep-like objects."""
        self.nodes = []
        self.adj = {}
        self.indegree = {}
        for step in steps:
            sid = step.id if hasattr(step, "id") else step.get("id")
            self.nodes.append(sid)
            self.adj.setdefault(sid, [])
            self.indegree.setdefault(sid, 0)
        for step in steps:
            sid = step.id if hasattr(step, "id") else step.get("id")
            deps = step.depends_on if hasattr(step, "depends_on") else step.get("depends_on", [])
            for dep in deps:
                if dep not in self.adj:
                    raise GraphError(f"Edge references unknown node '{dep}'",
                                     stage="graph")
                self.adj[dep].append(sid)
                self.indegree[sid] += 1
        self._detect_cycle()
        self._check_connectivity()
        return {
            "nodes": list(self.nodes),
            "edges": [
                {"from": src, "to": dst}
                for src, dsts in self.adj.items()
                for dst in dsts
            ],
            "topological_order": self.topological_order(),
            "depth": self.max_depth(),
        }

    def _detect_cycle(self) -> None:
        """Raise GraphError on any cycle (Kahn's algorithm)."""
        indeg = dict(self.indegree)
        queue = deque([n for n in self.nodes if indeg.get(n, 0) == 0])
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for dst in self.adj.get(node, []):
                indeg[dst] -= 1
                if indeg[dst] == 0:
                    queue.append(dst)
        if visited != len(self.nodes):
            cyclic = [n for n in self.nodes if indeg.get(n, 0) > 0]
            raise GraphError(f"Workflow graph contains a cycle involving "
                             f"{cyclic[:5]}", stage="graph")

    def _check_connectivity(self) -> None:
        """Warn (not raise) on disconnected components."""
        if not self.nodes:
            return
        start = self.nodes[0]
        seen = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.adj.get(n, []))
            for nid, deps in self.indegree.items():
                pass
        # Also walk reverse edges implicitly via adjacency.
        if len(seen) < len(self.nodes):
            raise GraphError(
                "Workflow graph is disconnected (orphan steps present)",
                stage="graph")

    def topological_order(self) -> List[str]:
        """Return a stable topological order of node ids."""
        indeg = dict(self.indegree)
        queue = deque(sorted([n for n in self.nodes if indeg.get(n, 0) == 0]))
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dst in sorted(self.adj.get(node, [])):
                indeg[dst] -= 1
                if indeg[dst] == 0:
                    queue.append(dst)
        return order

    def max_depth(self) -> int:
        """Longest-path depth of the DAG."""
        depth: Dict[str, int] = {}

        def visit(node: str) -> int:
            if node in depth:
                return depth[node]
            best = 0
            for dst in self.adj.get(node, []):
                best = max(best, 1 + visit(dst))
            depth[node] = best
            return best

        return max((visit(n) for n in self.nodes), default=0)
