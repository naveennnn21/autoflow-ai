"use client";

import { analyticsApi } from "./analytics";
import { executionsApi } from "./executions";
import { workflowsApi } from "./workflows";
import type { AnalyticsDashboard, Execution, Paginated, Workflow } from "@/types";

export interface DashboardData {
  metrics: AnalyticsDashboard["metrics"];
  series: AnalyticsDashboard["series"];
  recentActivity: AnalyticsDashboard["recentActivity"];
  recentExecutions: Execution[];
  counts: AnalyticsDashboard["counts"];
  workflows: Workflow[];
  activeWorkflows: Workflow[];
  totalWorkflows: number;
}

export async function getDashboardData(period: "7d" | "30d" | "90d" = "30d"): Promise<DashboardData> {
  const [analytics, workflows, executions] = await Promise.allSettled([
    analyticsApi.dashboard(period),
    workflowsApi.list({ page: 1, page_size: 100, sort_by: "updated_at", sort_order: "desc" }),
    executionsApi.list({ page: 1, page_size: 12, sort_by: "created_at", sort_order: "desc" }),
  ]);

  const dash: AnalyticsDashboard =
    analytics.status === "fulfilled"
      ? analytics.value
      : {
          metrics: [],
          series: [],
          failureDistribution: [],
          connectorHealth: [],
          healthSummary: {},
          topWorkflows: [],
          recentActivity: [],
          recentExecutions: [],
          counts: { workflows: 0, activeWorkflows: 0, connectors: 0, runs: 0, running: 0, retrying: 0, failed: 0 },
          period: { key: period, days: 0 },
        };

  const wfPage: Paginated<Workflow> =
    workflows.status === "fulfilled" ? workflows.value : { items: [], total: 0, page: 1, page_size: 100, total_pages: 0 };
  const execPage: Paginated<Execution> =
    executions.status === "fulfilled" ? executions.value : { items: [], total: 0, page: 1, page_size: 12, total_pages: 0 };

  const allWorkflows = wfPage.items ?? [];
  return {
    metrics: dash.metrics ?? [],
    series: dash.series ?? [],
    recentActivity: dash.recentActivity ?? [],
    recentExecutions: (dash.recentExecutions ?? []).length > 0 ? dash.recentExecutions : (execPage.items ?? []),
    counts: dash.counts ?? { workflows: 0, activeWorkflows: 0, connectors: 0, runs: 0, running: 0, retrying: 0, failed: 0 },
    workflows: allWorkflows,
    activeWorkflows: allWorkflows.filter((w) => w.status === "active"),
    totalWorkflows: wfPage.total ?? allWorkflows.length,
  };
}
