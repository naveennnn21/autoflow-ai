"use client";

import * as React from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
  addEdge,
  MarkerType,
} from "@xyflow/react";
import { CustomNode } from "./custom-node";
import { cn } from "@/lib/utils";
import type { ExecutionStatus, Workflow } from "@/types";

const nodeTypes = { custom: CustomNode };

function toNodes(wf: Workflow): Node[] {
  const width = 300;
  const height = 220;
  return wf.nodes.map((n, i) => ({
    id: n.id,
    type: "custom",
    position: { x: 120 + (i % 3) * width, y: 100 + Math.floor(i / 3) * height },
    data: { label: n.label, kind: n.kind, connector: n.connector, status: n.status ?? "waiting" },
  }));
}

function toEdges(wf: Workflow): Edge[] {
  return wf.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.animated ?? true,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { stroke: "hsl(var(--primary) / 0.5)", strokeWidth: 1.5 },
  }));
}

export interface FlowCanvasHandle {
  run: () => void;
}

export const FlowCanvas = React.forwardRef<FlowCanvasHandle, { workflow: Workflow }>(function FlowCanvas({ workflow }, ref) {
  const [nodes, setNodes, onNodesChange] = useNodesState(toNodes(workflow));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toEdges(workflow));
  const runningRef = React.useRef(false);
  const timersRef = React.useRef<number[]>([]);

  const onConnect = React.useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges],
  );

  const run = React.useCallback(() => {
    if (runningRef.current) return;
    runningRef.current = true;
    timersRef.current = [];
    const order = workflow.nodes.map((n) => n.id);
    const apply = (idx: number, status: ExecutionStatus) => {
      setNodes((nds) =>
        nds.map((n) => {
          const i = order.indexOf(n.id);
          if (i < idx) return { ...n, data: { ...n.data, status: "success" } };
          if (i === idx) return { ...n, data: { ...n.data, status } };
          return { ...n, data: { ...n.data, status: "waiting" } };
        }),
      );
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          animated: order.indexOf(e.target) <= idx,
          style: { stroke: order.indexOf(e.target) <= idx ? "hsl(var(--success))" : "hsl(var(--primary) / 0.4)", strokeWidth: 1.5 },
        })),
      );
    };
    order.forEach((_, idx) => {
      timersRef.current.push(
        window.setTimeout(() => apply(idx, idx === order.length - 1 ? "success" : "running"), idx * 900),
      );
    });
    timersRef.current.push(
      window.setTimeout(() => {
        apply(order.length, "success");
        runningRef.current = false;
      }, order.length * 900),
    );
  }, [setNodes, setEdges, workflow.nodes]);

  React.useImperativeHandle(ref, () => ({ run }), [run]);

  React.useEffect(() => {
    return () => {
      timersRef.current.forEach((t) => window.clearTimeout(t));
      timersRef.current = [];
    };
  }, []);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ type: "smoothstep" }}
        className={cn("rounded-xl border border-border bg-dots")}
      >
        <Background gap={24} size={1} color="hsl(var(--border))" />
        <Controls className="!rounded-lg !border-border !bg-card !shadow-soft" />
        <MiniMap
          pannable
          zoomable
          className="!rounded-lg !border-border !bg-card"
          nodeColor={(n) => (n.data?.status === "success" ? "hsl(var(--success))" : "hsl(var(--primary))" )}
        />
      </ReactFlow>
    </div>
  );
});
