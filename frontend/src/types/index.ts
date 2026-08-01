export type ExecutionStatus =
  | "waiting"
  | "running"
  | "retrying"
  | "success"
  | "failed"
  | "rollback"
  | "paused";

export type NodeKind = "trigger" | "action" | "condition" | "ai" | "delay" | "webhook";

export interface WorkflowNodeDef {
  id: string;
  kind: NodeKind;
  label: string;
  connector?: string;
  action?: string;
  description?: string;
  icon?: string;
  status?: ExecutionStatus;
  config?: Record<string, unknown>;
}

export interface WorkflowEdgeDef {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "active" | "draft" | "paused" | "archived";
  trigger: string;
  connectorIds: string[];
  runs: number;
  successRate: number;
  avgDurationMs: number;
  lastRunAt?: string;
  updatedAt: string;
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
  favorite?: boolean;
  tags?: string[];
}

export interface Execution {
  id: string;
  workflowId: string;
  workflowName: string;
  status: ExecutionStatus;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  error?: string;
  attempts: number;
  nodeProgress: Record<string, ExecutionStatus>;
  triggeredBy: string;
}

export type ConnectorAuthKind = "oauth2" | "api_key" | "bearer" | "basic" | "none";

export interface ConnectorAction {
  id: string;
  name: string;
  description: string;
  inputs: string[];
  outputs: string[];
  kind: "read" | "write" | "search" | "upload" | "batch";
}

export interface ConnectorTrigger {
  id: string;
  name: string;
  description: string;
  kind: "webhook" | "polling" | "cron" | "manual";
}

export interface Connector {
  id: string;
  slug: string;
  name: string;
  category: string;
  description: string;
  logo: string;
  color: string;
  auth: ConnectorAuthKind;
  scopes: string[];
  actions: ConnectorAction[];
  triggers: ConnectorTrigger[];
  rateLimit: string;
  health: "healthy" | "degraded" | "down";
  rating: number;
  installs: number;
  installed: boolean;
  verified?: boolean;
  popular?: boolean;
  tags?: string[];
}

export interface ActivityItem {
  id: string;
  type: "run" | "connector" | "deploy" | "alert" | "user";
  title: string;
  description: string;
  timestamp: string;
  status?: ExecutionStatus | "info" | "added" | "removed";
}

export interface Metric {
  id: string;
  label: string;
  value: number;
  unit?: string;
  delta: number;
  spark: number[];
  format?: "number" | "currency" | "percent" | "compact";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  streaming?: boolean;
  thinking?: boolean;
  clarifications?: string[];
  workflowPreview?: WorkflowPreview;
}

export interface WorkflowPreview {
  name: string;
  description: string;
  steps: { connector: string; action: string; label: string }[];
  estimate: string;
}

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: "admin" | "member";
  org: string;
}

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  badge?: string;
  group?: string;
}

export interface ToastAction {
  label: string;
  onClick?: () => void;
}

export interface PricingTier {
  name: string;
  price: number;
  cadence: string;
  description: string;
  features: string[];
  highlight?: boolean;
  cta: string;
}

export interface Testimonial {
  name: string;
  role: string;
  company: string;
  quote: string;
  avatarColor: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface Integration {
  name: string;
  logo: string;
  color: string;
  category?: string;
}

export interface Feature {
  icon: string;
  title: string;
  description: string;
  gradient: string;
}
