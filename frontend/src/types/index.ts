export type ExecutionStatus =
  | "waiting"
  | "running"
  | "retrying"
  | "success"
  | "failed"
  | "rollback"
  | "paused"
  | "cancelled"
  | "timeout";

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

export type WorkflowStatus = "active" | "draft" | "paused" | "archived" | "failed";

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
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
  health: "healthy" | "degraded" | "down" | "unknown";
  rating: number;
  installs: number;
  installed: boolean;
  verified?: boolean;
  popular?: boolean;
  tags?: string[];
  version?: string;
  capabilities?: {
    actions: boolean;
    triggers: boolean;
    webhook: boolean;
    polling: boolean;
  };
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

// ---------------------------------------------------------------------------
// Backend API shapes
// ---------------------------------------------------------------------------

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuthOrg {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: Record<string, unknown>;
  org: AuthOrg | null;
}

export interface BackendUser {
  id: string;
  email: string;
  full_name?: string | null;
  avatar_url?: string | null;
  status?: string;
  is_superuser?: boolean;
  is_verified?: boolean;
  created_at?: string | null;
  org?: AuthOrg | null;
  role?: string;
}

export interface BackendWorkflow {
  id: string;
  name: string;
  description?: string | null;
  status?: string | null;
  version?: number | null;
  config?: Record<string, unknown> | null;
  error_count?: number | null;
  last_run_at?: string | null;
  organization_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BackendExecution {
  id: string;
  workflow_id?: string | null;
  organization_id?: string | null;
  triggered_by?: string | null;
  status?: string | null;
  trigger_type?: string | null;
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  error_message?: string | null;
  duration_ms?: number | null;
  retry_attempt?: number | null;
  cost?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: Record<string, unknown>;
  is_active?: boolean;
  last_used_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url?: string | null;
  description?: string | null;
  is_active?: boolean | null;
  tier?: string | null;
  settings?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message?: string | null;
  type?: string | null;
  channel?: string | null;
  is_read?: boolean | null;
  created_at?: string;
}

export interface PlannerPreview {
  name: string;
  description: string;
  steps: { connector: string; action: string; label: string }[];
  estimate: string;
}

export interface PlannerChatResponse {
  reply: string;
  clarifications: string[];
  preview: PlannerPreview | null;
  plan: Record<string, unknown> | null;
  provider: string;
  model: string;
  latency_ms: number;
  warnings: string[];
  errors: string[];
}

export interface PlannerHealth {
  status: string;
  provider_configured: boolean;
  catalog: { count: number; connectors: string[] };
  metrics: Record<string, unknown>;
}

export interface SeriesPoint {
  date: string;
  runs: number;
  success: number;
  failed: number;
  latencyMs: number;
  cost: number;
}

export interface FailureBucket {
  label: string;
  count: number;
  pct: number;
}

export interface ConnectorHealthEntry {
  name: string;
  slug: string;
  health: "healthy" | "degraded" | "down" | "unknown";
}

export interface TopWorkflowEntry {
  workflowId: string;
  name: string;
  runs: number;
  successRate: number;
}

export interface AnalyticsDashboard {
  metrics: Metric[];
  series: SeriesPoint[];
  failureDistribution: FailureBucket[];
  connectorHealth: ConnectorHealthEntry[];
  healthSummary: Record<string, number>;
  topWorkflows: TopWorkflowEntry[];
  recentActivity: ActivityItem[];
  recentExecutions: Execution[];
  counts: {
    workflows: number;
    activeWorkflows: number;
    connectors: number;
    runs: number;
    running: number;
    retrying: number;
    failed: number;
  };
  period: { key: string; days: number };
}
