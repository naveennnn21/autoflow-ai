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
  type NodeMouseHandler,
  type NodeTypes,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { CustomNode } from "./custom-node";
import { NodeInspector } from "./node-inspector";
import { NodePalette } from "./node-palette";
import { cn } from "@/lib/utils";
import type { ExecutionStatus, Workflow, WorkflowEdgeDef, WorkflowNodeDef } from "@/types";

const nodeTypes: NodeTypes = { custom: CustomNode };

const COL_WIDTH = 300;
const COL_GAP = 60;
const ROW_HEIGHT = 230;
const START_X = 100;
const START_Y = 90;

const KIND_DEFAULT: Record<string, { label: string; connector?: string; action?: string }> = {
  trigger: { label: "New trigger", connector: "manual" },
  action: { label: "New action", connector: "slack", action: "post_message" },
  condition: { label: "Condition", connector: "condition" },
  ai: { label: "AI step", connector: "openai", action: "complete" },
  delay: { label: "Wait", connector: "wait" },
  webhook: { label: "Webhook", connector: "webhook", action: "receive" },
};

/**
 * Layered (topological-ish) layout: BFS levels from root nodes with no
 * incoming edges; nodes in the same level share a column so nothing
 * overlaps. Falls back to a simple grid for disconnected nodes.
 */
export function autoLayout(nodes: WorkflowNodeDef[], edges: WorkflowEdgeDef[]): { x: number; y: number }[] {
  const incoming: Record<string, number> = {};
  const outgoing: Record<string, string[]> = {};
  const ids = nodes.map((n) => n.id);
  for (const id of ids) {
    incoming[id] = 0;
    outgoing[id] = [];
  }
  for (const e of edges) {
    if (incoming[e.target] !== undefined) incoming[e.target] += 1;
    if (outgoing[e.source]) outgoing[e.source].push(e.target);
  }
  const roots = ids.filter((id) => incoming[id] === 0);
  const queue = [...roots];
  const level: Record<string, number> = {};
  for (const id of ids) level[id] = 0;
  const seen = new Set(queue);
  while (queue.length) {
    const id = queue.shift() as string;
    for (const child of outgoing[id] ?? []) {
      level[child] = Math.max(level[child] ?? 0, (level[id] ?? 0) + 1);
      if (!seen.has(child)) {
        seen.add(child);
        queue.push(child);
      }
    }
  }
  const byLevel: Record<number, string[]> = {};
  for (const id of ids) {
    const l = level[id] ?? 0;
    (byLevel[l] ??= []).push(id);
  }
  const maxLevel = Math.max(0, ...Object.keys(byLevel).map(Number));
  const result: { x: number; y: number }[] = [];
  const placed: Record<string, boolean> = {};
  for (let l = 0; l <= maxLevel; l++) {
    (byLevel[l] ?? []).forEach((id, i) => {
      result.push({ x: START_X + l * (COL_WIDTH + COL_GAP), y: START_Y + i * ROW_HEIGHT });
      placed[id] = true;
    });
  }
  // Any nodes never reached (isolated) - place on their own column.
  const isolated = ids.filter((id) => !placed[id]);
  isolated.forEach((id, i) => {
    result.push({ x: START_X + (maxLevel + 1) * (COL_WIDTH + COL_GAP), y: START_Y + i * ROW_HEIGHT });
  });
  return result;
}

function toNodes(wf: Workflow): Node[] {
  const layout = autoLayout(wf.nodes, wf.edges);
  return wf.nodes.map((n, i) => ({
    id: n.id,
    type: "custom",
    position: layout[i] ?? { x: START_X, y: START_Y + i * ROW_HEIGHT },
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

export interface FlowCanvasSnapshot {
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
}

export interface RunEvent {
  node_id: string;
  name?: string;
  node_type?: string;
  status: string;
  error?: string | null;
  attempts?: number;
  duration_ms?: number;
  output?: Record<string, unknown>;
}

export interface FlowCanvasHandle {
  run: (events: RunEvent[]) => void;
  applyRunEvent: (event: RunEvent) => void;
  getSnapshot: () => FlowCanvasSnapshot;
  clearRun: () => void;
}

export const FlowCanvas = React.forwardRef<FlowCanvasHandle, { workflow: Workflow }>(
  function FlowCanvas({ workflow }, ref) {
    const [nodes, setNodes, onNodesChange] = useNodesState(toNodes(workflow));
    const [edges, setEdges, onEdgesChange] = useEdgesState(toEdges(workflow));
    const [selectedId, setSelectedId] = React.useState<string | null>(null);
    const runningRef = React.useRef(false);

    const onConnect = React.useCallback(
      (params: Connection) => {
        const source = params.source;
        const target = params.target;
        if (!source || !target || source === target) return;
        setEdges((eds) => [
          ...eds,
          {
            ...params,
            id: `e_${source}_${target}_${Date.now().toString(36)}`,
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
            style: { stroke: "hsl(var(--primary) / 0.5)", strokeWidth: 1.5 },
          },
        ]);
      },
      [setEdges],
    );

    const onNodeClick: NodeMouseHandler = React.useCallback((_, node) => {
      setSelectedId((cur) => (cur === node.id ? null : (node.id as string)));
    }, []);

    const handleDeleteSelection = React.useCallback(() => {
      if (!selectedId) return;
      setNodes((nds) => nds.filter((n) => n.id !== selectedId));
      setEdges((eds) => eds.filter((e) => e.source !== selectedId && e.target !== selectedId));
      setSelectedId(null);
    }, [selectedId, setNodes, setEdges]);

    const addNode = React.useCallback(
      (kind: string) => {
        const defaults = KIND_DEFAULT[kind] ?? KIND_DEFAULT.action;
        const id = `${kind}_${Date.now().toString(36)}`;
        const position = { x: 120 + (nodes.length % 3) * 60, y: 120 + nodes.length * 20 };
        setNodes((nds) => [
          ...nds,
          {
            id,
            type: "custom",
            position,
            data: { label: defaults.label, kind, connector: defaults.connector, status: "waiting" },
          },
        ]);
      },
      [nodes.length, setNodes],
    );

    const updateSelected = React.useCallback(
      (patch: Partial<{ label: string; connector: string; action: string; prompt: string }>) => {
        if (!selectedId) return;
        setNodes((nds) =>
          nds.map((n) => {
            if (n.id !== selectedId) return n;
            const data = { ...(n.data ?? {}), ...patch };
            return { ...n, data };
          }),
        );
      },
      [selectedId, setNodes],
    );

    const clearRun = React.useCallback(() => {
      setNodes((nds) =>
        nds.map((n) => ({ ...n, data: { ...n.data, status: "waiting" } })),
      );
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          animated: true,
          style: { stroke: "hsl(var(--primary) / 0.5)", strokeWidth: 1.5 },
        })),
      );
    }, [setNodes, setEdges]);

    const run = React.useCallback(
      (events: RunEvent[]) => {
        runningRef.current = true;
        const completed = new Set<string>();
        const failed = new Set<string>();
        for (const ev of events) {
          if (ev.status === "completed") completed.add(ev.node_id);
          if (ev.status === "failed") failed.add(ev.node_id);
        }
        setNodes((nds) =>
          nds.map((n) => {
            const data = { ...n.data };
            if (failed.has(n.id)) data.status = "failed";
            else if (completed.has(n.id)) data.status = "success";
            else data.status = "running";
            const ev = events.find((e) => e.node_id === n.id);
            if (ev?.error) data.error = ev.error;
            return { ...n, data };
          }),
        );
        setEdges((eds) =>
          eds.map((e) => ({
            ...e,
            animated: completed.has(e.target) || failed.has(e.target),
            style: {
              stroke: failed.has(e.target)
                ? "hsl(var(--destructive))"
                : completed.has(e.target)
                  ? "hsl(var(--success))"
                  : "hsl(var(--primary) / 0.5)",
              strokeWidth: completed.has(e.target) || failed.has(e.target) ? 2 : 1.5,
            },
          })),
        );
        setTimeout(() => {
          runningRef.current = false;
        }, 300);
      },
      [setNodes, setEdges],
    );

    const applyRunEvent = React.useCallback(
      (event: RunEvent) => {
        setNodes((nds) =>
          nds.map((n) => {
            if (n.id !== event.node_id) return n;
            const data = { ...n.data };
            data.status =
              event.status === "completed"
                ? "success"
                : event.status === "failed"
                  ? "failed"
                  : (event.status as ExecutionStatus);
            if (event.error) data.error = event.error;
            return { ...n, data };
          }),
        );
        if (event.status === "completed" || event.status === "failed") {
          setEdges((eds) =>
            eds.map((e) =>
              e.target === event.node_id
                ? {
                    ...e,
                    animated: false,
                    style: {
                      stroke:
                        event.status === "failed"
                          ? "hsl(var(--destructive))"
                          : "hsl(var(--success))",
                      strokeWidth: 2,
                    },
                  }
                : e,
            ),
          );
        }
      },
      [setNodes, setEdges],
    );

    const getSnapshot = React.useCallback(
      (): FlowCanvasSnapshot => ({
        nodes: nodes.map((n) => ({
          id: n.id,
          kind: (n.data?.kind ?? "action") as WorkflowNodeDef["kind"],
          label: String(n.data?.label ?? n.id),
          connector: (n.data?.connector as string | undefined) ?? undefined,
          action: (n.data?.action as string | undefined) ?? undefined,
          config:
            n.data?.prompt !== undefined
              ? { ...(n.data.config as Record<string, unknown> | undefined), prompt: n.data.prompt }
              : (n.data?.config as Record<string, unknown> | undefined),
          status: undefined,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: typeof e.label === "string" ? e.label : undefined,
          animated: e.animated ?? true,
        })),
      }),
      [nodes, edges],
    );

    React.useImperativeHandle(
      ref,
      () => ({ run, applyRunEvent, getSnapshot, clearRun }),
      [run, applyRunEvent, getSnapshot, clearRun],
    );

    return (
      <div className="flex h-full w-full gap-3">
        <NodePalette onAdd={addNode} disabled={runningRef.current} />
        <div className="relative min-h-0 min-w-0 flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedId(null)}
            nodeTypes={nodeTypes}
            fitView
            deleteKeyCode={["Backspace", "Delete"]}
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
              nodeColor={(n) =>
                n.data?.status === "success"
                  ? "hsl(var(--success))"
                  : n.data?.status === "failed"
                    ? "hsl(var(--destructive))"
                    : "hsl(var(--primary))"
              }
            />
          </ReactFlow>
        </div>
        <NodeInspector
          node={
            selectedId
              ? nodes.find((n) => n.id === selectedId) ?? null
              : null
          }
          onChange={updateSelected}
          onDelete={handleDeleteSelection}
        />
      </div>
    );
  },
);
