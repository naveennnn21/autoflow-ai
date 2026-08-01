import type { ActivityItem, Execution, Metric } from "@/types";

const now = Date.now();
const mins = (m: number) => new Date(now - m * 60000).toISOString();
const hours = (h: number) => new Date(now - h * 3600000).toISOString();
const days = (d: number) => new Date(now - d * 86400000).toISOString();

export const metrics: Metric[] = [
  {
    id: "runs", label: "Total Runs", value: 128452, delta: 12.4, format: "compact",
    spark: [42, 48, 45, 52, 58, 55, 63, 68, 72, 70, 78, 84],
  },
  {
    id: "success", label: "Success Rate", value: 98.6, unit: "%", delta: 0.8, format: "percent",
    spark: [97, 97.5, 98, 97.8, 98.2, 98, 98.4, 98.5, 98.6, 98.4, 98.6, 98.6],
  },
  {
    id: "latency", label: "Avg Latency", value: 1.24, unit: "s", delta: -8.2, format: "number",
    spark: [2.1, 1.9, 1.8, 1.7, 1.6, 1.55, 1.5, 1.42, 1.38, 1.3, 1.27, 1.24],
  },
  {
    id: "cost", label: "Monthly Cost", value: 842, unit: "$", delta: 5.1, format: "currency",
    spark: [720, 740, 735, 770, 760, 790, 810, 800, 825, 830, 845, 842],
  },
];

export const executions: Execution[] = [
  {
    id: "exe_91a2", workflowId: "wf_support_triage", workflowName: "Support Ticket Triage",
    status: "running", startedAt: mins(0.4), attempts: 1,
    nodeProgress: { n1: "success", n2: "success", n3: "running", n4: "waiting" },
    triggeredBy: "New Email",
  },
  {
    id: "exe_88f1", workflowId: "wf_lead_intel", workflowName: "Lead Intelligence Pipeline",
    status: "success", startedAt: mins(4), finishedAt: mins(3.9), durationMs: 4120, attempts: 1,
    nodeProgress: { n1: "success", n2: "success", n3: "success", n4: "success", n5: "success" },
    triggeredBy: "Contact Created",
  },
  {
    id: "exe_85b3", workflowId: "wf_onboarding", workflowName: "Customer Onboarding",
    status: "success", startedAt: mins(22), finishedAt: mins(21.9), durationMs: 1930, attempts: 1,
    nodeProgress: { n1: "success", n2: "success", n3: "success", n4: "success" },
    triggeredBy: "Customer Created",
  },
  {
    id: "exe_80c7", workflowId: "wf_support_triage", workflowName: "Support Ticket Triage",
    status: "retrying", startedAt: hours(1.1), attempts: 2,
    nodeProgress: { n1: "success", n2: "success", n3: "failed", n4: "waiting" },
    triggeredBy: "New Email",
  },
  {
    id: "exe_77d9", workflowId: "wf_lead_intel", workflowName: "Lead Intelligence Pipeline",
    status: "failed", startedAt: hours(2.3), finishedAt: hours(2.2), durationMs: 8900, attempts: 3,
    error: "Rate limit exceeded on github:enrich_profile (429)",
    nodeProgress: { n1: "success", n2: "retrying", n3: "waiting", n4: "waiting", n5: "waiting" },
    triggeredBy: "Contact Created",
  },
  {
    id: "exe_71e5", workflowId: "wf_weekly_report", workflowName: "Weekly Revenue Digest",
    status: "success", startedAt: days(2), finishedAt: days(2), durationMs: 5810, attempts: 1,
    nodeProgress: { n1: "success", n2: "success", n3: "success", n4: "success" },
    triggeredBy: "Cron",
  },
  {
    id: "exe_69aa", workflowId: "wf_inventory_sync", workflowName: "Inventory Sync",
    status: "rollback", startedAt: days(4), finishedAt: days(4), durationMs: 15400, attempts: 2,
    error: "Constraint violation on postgres:insert_row",
    nodeProgress: { n1: "success", n2: "success", n3: "failed" },
    triggeredBy: "Cron",
  },
];

export const activity: ActivityItem[] = [
  {
    id: "a1", type: "run", title: "Support Ticket Triage completed",
    description: "Classified 12 emails · 1 urgent routed to #support-urgent",
    timestamp: mins(4), status: "success",
  },
  {
    id: "a2", type: "deploy", title: "Lead Intelligence Pipeline deployed",
    description: "Version 14 · 5 nodes · 4 connectors",
    timestamp: hours(3), status: "info",
  },
  {
    id: "a3", type: "alert", title: "github:enrich_profile rate limited",
    description: "429 · retry attempt 2 of 3 · backoff 4.2s",
    timestamp: hours(2.2), status: "failed",
  },
  {
    id: "a4", type: "connector", title: "Stripe connected",
    description: "Acme Corp · scopes: charges, customers, subscriptions",
    timestamp: hours(6), status: "added",
  },
  {
    id: "a5", type: "run", title: "Customer Onboarding completed",
    description: "Welcome email sent · Notion row created",
    timestamp: mins(22), status: "success",
  },
  {
    id: "a6", type: "user", title: "Priya invited to workspace",
    description: "Role: member · joined 2 hours ago",
    timestamp: hours(26), status: "info",
  },
  {
    id: "a7", type: "connector", title: "Linear health degraded",
    description: "P95 latency above 2s · monitoring",
    timestamp: hours(30), status: "removed",
  },
  {
    id: "a8", type: "run", title: "Weekly Revenue Digest completed",
    description: "$12,480 MRR summarized · email sent",
    timestamp: days(2), status: "success",
  },
];
