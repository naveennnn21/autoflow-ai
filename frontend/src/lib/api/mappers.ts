/**
 * Backend -> frontend data mappers.
 *
 * The backend serializes ORM rows with snake_case fields and stores
 * workflow display metadata (nodes, edges, run stats) inside the
 * workflow `config` JSON. These mappers normalize both into the
 * frontend types used across pages.
 */
import type {
  BackendExecution,
  BackendUser,
  BackendWorkflow,
  Connector,
  Execution,
  ExecutionStatus,
  SessionUser,
  Workflow,
  WorkflowEdgeDef,
  WorkflowNodeDef,
} from "@/types";

const executionStatusMap: Record<string, ExecutionStatus> = {
  completed: "success",
  success: "success",
  pending: "waiting",
  waiting: "waiting",
  running: "running",
  retrying: "retrying",
  failed: "failed",
  paused: "paused",
  rollback: "rollback",
  cancelled: "cancelled",
  timeout: "timeout",
};

export function toFrontendStatus(status?: string | null): ExecutionStatus {
  return executionStatusMap[(status ?? "pending").toLowerCase()] ?? "waiting";
}

export function toBackendStatus(status: ExecutionStatus): string {
  switch (status) {
    case "success":
      return "completed";
    case "waiting":
      return "pending";
    default:
      return status;
  }
}

/** Serialize the frontend Workflow extras back into the backend `config` JSON. */
export function toBackendConfig(wf: Workflow): Record<string, unknown> {
  return {
    trigger: wf.trigger,
    connectorIds: wf.connectorIds,
    runs: wf.runs,
    successRate: wf.successRate,
    avgDurationMs: wf.avgDurationMs,
    favorite: wf.favorite ?? false,
    tags: wf.tags ?? [],
    nodes: wf.nodes,
    edges: wf.edges,
    ...(wf.lastRunAt ? { lastRunAt: wf.lastRunAt } : {}),
  };
}

export function mapWorkflow(raw: BackendWorkflow): Workflow {
  const cfg = (raw.config ?? {}) as Record<string, unknown>;
  return {
    id: raw.id,
    name: raw.name,
    description: (raw.description ?? cfg.description ?? "") as string,
    status: (raw.status ?? "draft") as Workflow["status"],
    trigger: (cfg.trigger ?? "manual") as string,
    connectorIds: Array.isArray(cfg.connectorIds) ? (cfg.connectorIds as string[]) : [],
    runs: Number(cfg.runs ?? 0),
    successRate: Number(cfg.successRate ?? 0),
    avgDurationMs: Number(cfg.avgDurationMs ?? 0),
    lastRunAt: (cfg.lastRunAt ?? raw.last_run_at ?? undefined) as string | undefined,
    updatedAt: raw.updated_at ?? new Date().toISOString(),
    nodes: Array.isArray(cfg.nodes) ? (cfg.nodes as WorkflowNodeDef[]) : [],
    edges: Array.isArray(cfg.edges) ? (cfg.edges as WorkflowEdgeDef[]) : [],
    favorite: Boolean(cfg.favorite),
    tags: Array.isArray(cfg.tags) ? (cfg.tags as string[]) : [],
  };
}

export function mapExecution(
  raw: BackendExecution,
  workflowNames: Record<string, string> = {},
): Execution {
  const wfId = raw.workflow_id ?? "";
  const rawName = (raw as { workflow_name?: string | null }).workflow_name;
  return {
    id: raw.id,
    workflowId: wfId,
    workflowName: workflowNames[wfId] ?? rawName ?? (wfId || "Unknown workflow"),
    status: toFrontendStatus(raw.status),
    startedAt: raw.started_at ?? raw.created_at ?? new Date().toISOString(),
    finishedAt: raw.completed_at ?? undefined,
    durationMs: raw.duration_ms ?? undefined,
    error: raw.error_message || undefined,
    attempts: Math.max(1, (raw.retry_attempt ?? 0) + 1),
    nodeProgress: {},
    triggeredBy: raw.trigger_type ?? "manual",
  };
}

export function mapConnector(raw: Record<string, unknown>): Connector {
  const health = (raw.health as Connector["health"]) ?? "unknown";
  return {
    id: (raw.id as string) ?? (raw.slug as string) ?? "",
    slug: (raw.slug as string) ?? "",
    name: (raw.name as string) ?? "Connector",
    category: (raw.category as string) ?? "General",
    description: (raw.description as string) ?? "",
    logo: (raw.logo as string) ?? "plug",
    color: (raw.color as string) ?? "#6366f1",
    auth: (raw.auth as Connector["auth"]) ?? "none",
    scopes: Array.isArray(raw.scopes) ? (raw.scopes as string[]) : [],
    actions: Array.isArray(raw.actions) ? (raw.actions as Connector["actions"]) : [],
    triggers: Array.isArray(raw.triggers) ? (raw.triggers as Connector["triggers"]) : [],
    rateLimit: (raw.rateLimit as string) ?? "-",
    health: ["healthy", "degraded", "down", "unknown"].includes(health) ? health : "unknown",
    rating: Number(raw.rating ?? 0),
    installs: Number(raw.installs ?? 0),
    installed: Boolean(raw.installed),
    verified: Boolean(raw.verified),
    popular: Boolean(raw.popular),
    tags: Array.isArray(raw.tags) ? (raw.tags as string[]) : [],
    version: (raw.version as string) ?? undefined,
    capabilities: raw.capabilities as Connector["capabilities"],
  };
}

export function mapSessionUser(raw: Record<string, unknown>): SessionUser {
  const org = (raw.org ?? {}) as Record<string, unknown> | null;
  const role = (raw.role as string) ?? org?.role ?? "member";
  return {
    id: (raw.id as string) ?? "",
    name: (raw.full_name as string) ?? (raw.name as string) ?? (raw.email as string) ?? "User",
    email: (raw.email as string) ?? "",
    avatar: (raw.avatar_url as string) ?? undefined,
    role: role === "admin" || role === "owner" ? "admin" : "member",
    org: (org?.name as string) ?? (raw.org_name as string) ?? "Workspace",
  };
}

export function mapBackendUser(raw: BackendUser): SessionUser {
  return mapSessionUser(raw as unknown as Record<string, unknown>);
}
