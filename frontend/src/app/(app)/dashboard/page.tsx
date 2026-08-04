"use client";

import { useSession } from "@/stores/session";
import { MetricCard } from "@/components/dashboard/metric-card";
import { OverviewChart } from "@/components/dashboard/charts";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { ExecutionsTable } from "@/components/dashboard/executions-table";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { metrics, executions, activity } from "@/lib/mock-analytics";
import { workflows } from "@/lib/mock-workflows";
import { FadeIn } from "@/components/motion/fade-in";

export default function DashboardPage() {
  const user = useSession((s) => s.user);
  const greeting = user?.name?.split(" ")[0] ?? "there";

  return (
    <div className="max-w-7xl mx-auto space-y-10">
      {/* Greeting + status */}
      <FadeIn>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[13px] font-medium uppercase tracking-[0.12em] text-muted-foreground/70">
              {new Date().getHours() < 12 ? "Morning" : new Date().getHours() < 18 ? "Afternoon" : "Evening"}
            </p>
            <h1 className="text-title mt-0.5">Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}, {greeting}.</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3.5 py-1.5 text-xs font-medium text-success">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-soft" />
              All systems nominal
            </div>
            <Button asChild size="sm" className="gap-1.5">
              <Link href="/chat">
                <Sparkles className="h-3.5 w-3.5" />
                Build with AI
              </Link>
            </Button>
          </div>
        </div>
      </FadeIn>

      {/* Metrics */}
      <StaggerGroup className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((m) => (
          <StaggerItem key={m.id}>
            <MetricCard metric={m} />
          </StaggerItem>
        ))}
      </StaggerGroup>

      {/* Chart + Activity */}
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Executions over time</p>
            <Badge variant="secondary">Last 30 days</Badge>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-sm">
            <OverviewChart />
          </div>
        </div>
        <div className="space-y-3">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Activity</p>
          <ActivityFeed items={activity.slice(0, 6)} />
        </div>
      </div>

      {/* Active Workflows + Recent executions */}
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Recent executions</p>
            <Link href="/workflows" className="group inline-flex items-center gap-1 text-xs font-medium text-primary">
              View all <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur-sm">
            <ExecutionsTable executions={executions.slice(0, 6)} />
          </div>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active workflows</p>
            <Badge variant="success" className="text-[10px]">{workflows.filter(w => w.status === "active").length} running</Badge>
          </div>
          <div className="space-y-3">
            {workflows.filter((w) => w.status === "active").slice(0, 4).map((wf) => (
              <Link
                key={wf.id}
                href={`/workflows/${wf.id}/builder`}
                className="group block rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-sm transition-colors hover:border-border/90"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{wf.name}</p>
                    <p className="truncate text-xs text-muted-foreground mt-0.5">{wf.trigger}</p>
                  </div>
                  <span className="flex h-6 w-6 items-center justify-center rounded-full border border-success/30 bg-success/10">
                    <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-soft" />
                  </span>
                </div>
                <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{(wf.runs / 1000).toFixed(1)}k runs</span>
                  <span className="text-success">{wf.successRate}%</span>
                  <span className="ml-auto font-mono text-[10px]">{wf.avgDurationMs ? `${(wf.avgDurationMs / 1000).toFixed(1)}s` : "—"}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}