"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { OverviewChart } from "@/components/dashboard/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { MetricSkeleton, Skeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge, ConnectorHealthBadge } from "@/components/shared/status-badge";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { analyticsApi, type AnalyticsPeriod } from "@/lib/api/analytics";
import { cn } from "@/lib/utils";

const healthBar = { healthy: 100, degraded: 60, down: 20, unknown: 0 } as const;

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("30d");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.analytics(period),
    queryFn: () => analyticsApi.dashboard(period),
  });

  const healthSummary = data?.healthSummary ?? { healthy: 0, degraded: 0, down: 0, unknown: 0 };

  return (
    <div className="space-y-8">
      <PageHeader title="Analytics" description="Usage, latency, cost, and reliability across your workspace.">
        <Select value={period} onValueChange={(v) => setPeriod(v as AnalyticsPeriod)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
            <SelectItem value="90d">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </PageHeader>

      {isError ? (
        <EmptyState
          title="Couldn't load analytics"
          description="The analytics API is unreachable. Check that the backend is running."
          action={
            <Button variant="outline" size="sm" className="gap-2" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Retry
            </Button>
          }
        />
      ) : (
        <>
          <StaggerGroup className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {isLoading
              ? Array.from({ length: 4 }).map((_, i) => <MetricSkeleton key={i} />)
              : (data?.metrics ?? []).map((m) => (
                  <StaggerItem key={m.id}>
                    <MetricCard metric={m} />
                  </StaggerItem>
                ))}
          </StaggerGroup>

          <div className="grid gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              {isLoading ? (
                <div className="rounded-2xl border border-border/60 bg-card/60 p-4">
                  <Skeleton className="h-72 w-full" />
                </div>
              ) : (
                <OverviewChart series={data?.series ?? []} />
              )}
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Connector health</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="success">{healthSummary.healthy} healthy</Badge>
                  {healthSummary.degraded > 0 && <Badge variant="warning">{healthSummary.degraded} degraded</Badge>}
                  {(healthSummary.down ?? 0) > 0 && <Badge variant="destructive">{healthSummary.down} down</Badge>}
                  {(healthSummary.unknown ?? 0) > 0 && <Badge variant="secondary">{healthSummary.unknown} unknown</Badge>}
                </div>
                {isLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-9 w-full" />
                    ))}
                  </div>
                ) : (data?.connectorHealth ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No connectors registered yet.</p>
                ) : (
                  (data?.connectorHealth ?? []).slice(0, 8).map((c) => (
                    <div key={c.slug} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{c.name}</span>
                        <ConnectorHealthBadge health={c.health} />
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-1000",
                            c.health === "degraded" && "bg-warning",
                            c.health === "down" && "bg-destructive",
                            c.health === "unknown" && "bg-muted-foreground/40",
                            c.health === "healthy" && "bg-success",
                          )}
                          style={{ width: `${healthBar[c.health] ?? 0}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Recent executions</CardTitle>
              </CardHeader>
              <CardContent className="divide-y divide-border">
                {isLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-12 w-full" />
                    ))}
                  </div>
                ) : (data?.recentExecutions ?? []).length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No executions in this period. Run a workflow to see results here.
                  </p>
                ) : (
                  (data?.recentExecutions ?? []).slice(0, 8).map((ex) => (
                    <div key={ex.id} className="flex items-center gap-3 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{ex.workflowName}</p>
                        <p className="text-xs text-muted-foreground">{ex.triggeredBy} · attempt {ex.attempts}</p>
                      </div>
                      {ex.error && <p className="hidden max-w-[40%] truncate font-mono text-[11px] text-destructive lg:block">{ex.error}</p>}
                      <StatusBadge status={ex.status} />
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Failure distribution</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {isLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} className="h-9 w-full" />
                    ))}
                  </div>
                ) : (data?.failureDistribution ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No failures in this period. 🎉</p>
                ) : (
                  (data?.failureDistribution ?? []).map((f) => (
                    <div key={f.label}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{f.label}</span>
                        <span className="tabular-nums">{f.pct}%</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-purple to-brand-cyan"
                          style={{ width: `${f.pct}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
                <div className="flex items-center gap-2 pt-2">
                  <Badge variant="secondary">{data?.counts.runs ?? 0} runs this period</Badge>
                  {(data?.counts.failed ?? 0) > 0 && <Badge variant="warning">{data?.counts.failed} failed</Badge>}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
