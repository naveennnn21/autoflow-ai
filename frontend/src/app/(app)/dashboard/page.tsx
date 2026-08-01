"use client";

import { PageHeader } from "@/components/shared/page-header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { OverviewChart } from "@/components/dashboard/charts";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { ExecutionsTable } from "@/components/dashboard/executions-table";
import { WorkflowCard } from "@/components/dashboard/workflow-card";
import { Button } from "@/components/ui/button";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { metrics, executions, activity } from "@/lib/mock-analytics";
import { workflows } from "@/lib/mock-workflows";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Good morning, Ava"
        description="Here's what's happening across your automations."
      >
        <Button asChild>
          <Link href="/chat">
            <Sparkles className="h-4 w-4" />
            Build with AI
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/workflows">
            <Plus className="h-4 w-4" />
            New workflow
          </Link>
        </Button>
      </PageHeader>

      <StaggerGroup className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((m) => (
          <StaggerItem key={m.id}>
            <MetricCard metric={m} />
          </StaggerItem>
        ))}
      </StaggerGroup>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <OverviewChart />
        </div>
        <ActivityFeed items={activity.slice(0, 5)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ExecutionsTable executions={executions.slice(0, 6)} />
        </div>
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Favorite workflows</h2>
          {workflows.filter((w) => w.favorite).slice(0, 3).map((wf) => (
            <WorkflowCard key={wf.id} workflow={wf} />
          ))}
        </div>
      </div>
    </div>
  );
}
