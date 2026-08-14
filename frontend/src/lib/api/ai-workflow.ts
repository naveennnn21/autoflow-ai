"use client";

import { api, streamSse, type SseFrame } from "./client";
import type { WorkflowEdgeDef, WorkflowNodeDef } from "@/types";

export interface AiDefinition {
  name: string;
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
}

export interface ValidateResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  node_count: number;
  edge_count: number;
}

export interface DeployResult {
  ok: boolean;
  status: string;
  workflow_id?: string;
  version?: number | null;
  errors: string[];
  warnings: string[];
  spec?: Record<string, unknown> | null;
  diagnostics?: {
    errors?: string[];
    node_count?: number;
    edge_count?: number;
    undefined_variables?: string[];
    total_ms?: number;
    stage_times_ms?: Record<string, number>;
  };
  version_record_error?: string;
}

export interface VersionSnapshot {
  version: number;
  spec?: Record<string, unknown>;
  definition?: {
    name?: string;
    nodes?: WorkflowNodeDef[];
    edges?: WorkflowEdgeDef[];
  };
  compiler_version?: string;
  planner_version?: string;
  created_at?: string;
}

export interface VersionsResult {
  workflow_id: string;
  current_version: number | null;
  versions: VersionSnapshot[];
}

export interface DiffResult {
  workflow_id: string;
  from_version: number;
  to_version: number;
  added_nodes: string[];
  removed_nodes: string[];
}

export interface ExecuteResult {
  execution_id: string;
  workflow_id: string;
  status: string;
}

export interface ExecutionDetail {
  execution_id: string;
  status: string;
  error?: string | null;
  node_states: Record<string, string>;
  node_results?: Record<string, Record<string, unknown>>;
  finished?: boolean;
}

export interface ControlResult {
  execution_id: string;
  action: string;
  status: string;
}

export interface RunEventHandlers {
  onNode?: (event: {
    node_id: string;
    name: string;
    node_type: string;
    status: string;
    error?: string | null;
    attempts?: number;
    duration_ms?: number;
    output?: Record<string, unknown>;
  }) => void;
  onState?: (event: Record<string, unknown>) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

export const aiWorkflowApi = {
  validate: (definition: AiDefinition) =>
    api.post<ValidateResult>("/ai_workflow/validate", { definition }),

  deploy: (definition: AiDefinition, workflowId?: string, description?: string) =>
    api.post<DeployResult>("/ai_workflow/deploy", {
      definition,
      workflow_id: workflowId,
      description,
    }),

  versions: (workflowId: string) =>
    api.get<VersionsResult>(`/ai_workflow/workflows/${workflowId}/versions`),

  diff: (workflowId: string, fromVersion: number, toVersion: number) =>
    api.get<DiffResult>(
      `/ai_workflow/versions/diff?workflow_id=${encodeURIComponent(workflowId)}&from_version=${fromVersion}&to_version=${toVersion}`,
    ),

  execute: (workflowId: string, definition?: AiDefinition, inputs: Record<string, unknown> = {}) =>
    api.post<ExecuteResult>("/ai_workflow/execute", {
      workflow_id: workflowId,
      definition,
      inputs,
    }),

  detail: (executionId: string) =>
    api.get<ExecutionDetail>(`/ai_workflow/executions/${executionId}`),

  control: (executionId: string, action: "cancel" | "pause" | "resume" | "retry") =>
    api.post<ControlResult>(`/ai_workflow/executions/${executionId}/control`, { action }),

  streamExecution: (executionId: string, handlers: RunEventHandlers) =>
    streamSse(`/ai_workflow/executions/${executionId}/stream`, {
      method: "GET",
      onFrame: (frame: SseFrame) => {
        switch (frame.event) {
          case "node":
            handlers.onNode?.(frame.data as never);
            break;
          case "state":
            handlers.onState?.(frame.data);
            break;
          case "error":
            handlers.onError?.(new Error(String(frame.data.message ?? "Execution error")));
            break;
          case "done":
            handlers.onDone?.();
            break;
          default:
            break;
        }
      },
      onError: (err) => handlers.onError?.(err),
      onClose: () => handlers.onDone?.(),
    }),
};
