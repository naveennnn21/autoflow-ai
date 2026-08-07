"use client";

import { useSession } from "@/stores/session";
import { MetricCard } from "@/components/dashboard/metric-card";
import { OverviewChart } from "@/components/dashboard/charts";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { ExecutionsTable } from "@/components/dashboard/executions-table";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { FadeIn } from "@/components/motion/fade-in";
import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import { MetricSkeleton, Skeleton } from "@/components/shared/skeleton";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { getDashboardData } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";
import Link from "next/link";

function greetingFor(userName?: string): { time: string; text: string } {
  const hour = new Date().getHours();
  const time = hour < 12 ? "Morning" : hour < 18 ? "Afternoon" : "Evening";
  const name = userName?.split(" ")[0] ?? "there";
  return { time, text: `${time}, ${name}.` };
}

export default function DashboardPage() {
  const user = useSession((s) => s.user);
  const greeting = greetingFor(user?.name);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => getDashboardData("30d"),
  });

  const nominal =
    !!data &&
    data.counts.failed === 0 &&
    (data.metrics.length > 0 || data.totalWorkflows > 0);

  return (
    <div className="max-w-7xl mx-auto space-y-10">
      {/* Greeting + status */}
      <FadeIn>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[13px] font-medium uppercase tracking-[0.12em] text-muted-foreground/70">
              {greeting.time}
            </p>
            <h1 className="text-title mt-0.5">Good {greeting.text}</h1>
          </div>
          <div className="flex items-center gap-3">
            {isLoading ? (
              <Skeleton className="h-7 w-40 rounded-full" />
            ) : isError ? (
              <div className="flex items-center gap-2 rounded-full border border-destructive/30 bg-destructive/10 px-3.5 py-1.5 text-xs font-medium text-destructive">
                <span className="h-1.5 w-1.5 rounded-full bg-destructive animate-pulse-soft" />
                API unreachable
              </div>
            ) : (
              <div
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium",
                  nominal
                    ? "border-success/30 bg-success/10 text-success"
                    : "border-warning/30 bg-warning/10 text-warning",
                )}
              >
                <span className={cn("h-1.5 w-1.5 rounded-full animate-pulse-soft", nominal ? "bg-success" : "bg-warning")} />
                {nominal ? "All systems nominal" : "Some runs need attention"}
              </div>
            )}
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
      {isError ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-10 text-center">
          <p className="font-medium">Couldn&apos;t load your dashboard</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
            We couldn&apos;t reach the AutoFlow API. Check that the backend is running and try again.
          </p>
          <Button variant="outline" className="mt-4 gap-2" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Retry
          </Button>
        </div>
      ) : (
        <StaggerGroup className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => <MetricSkeleton key={i} />)
            : (data?.metrics ?? []).map((m) => (
                <StaggerItem key={m.id}>
                  <MetricCard metric={m} />
                </StaggerItem>
              ))}
        </StaggerGroup>
      )}

      {/* Chart + Activity */}
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Executions over time</p>
            <Badge variant="secondary">Last 30 days</Badge>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-sm">
            {isLoading ? (
              <div className="flex h-72 items-center justify-center">
                <Skeleton className="h-full w-full" />
              </div>
            ) : (
              <OverviewChart series={data?.series ?? []} />
            )}
          </div>
        </div>
        <div className="space-y-3">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Activity</p>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (data?.recentActivity ?? []).length === 0 ? (
            <EmptyState title="No activity yet" description="Workflow runs and workspace events will show up here." />
          ) : (
            <ActivityFeed items={(data?.recentActivity ?? []).slice(0, 6)} />
          )}
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
            {isLoading ? (
              <div className="space-y-1 p-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : (data?.recentExecutions ?? []).length === 0 ? (
              <div className="p-6">
                <EmptyState
                  title="No executions yet"
                  description="Once your workflows run, their executions will appear here."
                />
              </div>
            ) : (
              <ExecutionsTable executions={(data?.recentExecutions ?? []).slice(0, 6)} />
            )}
          </div>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active workflows</p>
            <Badge variant="success" className="text-[10px]">
              {(data?.activeWorkflows ?? []).length} running
            </Badge>
          </div>
          <div className="space-y-3">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
            ) : (data?.activeWorkflows ?? []).length === 0 ? (
              <EmptyState
                title="No active workflows"
                description="Design your first automation with the AI copilot."
                action={
                  <Button asChild size="sm" className="gap-1.5">
                    <Link href="/chat">
                      <Sparkles className="h-3.5 w-3.5" /> Build with AI
                    </Link>
                  </Button>
                }
              />
            ) : (
              (data?.activeWorkflows ?? []).slice(0, 4).map((wf) => (
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
                    <span>{wf.runs > 0 ? `${(wf.runs / 1000).toFixed(1)}k runs` : "No runs yet"}</span>
                    {wf.successRate > 0 && <span className="text-success">{wf.successRate}%</span>}
                    <span className="ml-auto font-mono text-[10px]">
                      {wf.avgDurationMs ? `${(wf.avgDurationMs / 1000).toFixed(1)}s` : "—"}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
