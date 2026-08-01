"use client";

import { PageHeader } from "@/components/shared/page-header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { OverviewChart } from "@/components/dashboard/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { metrics, executions } from "@/lib/mock-analytics";
import { StatusBadge } from "@/components/shared/status-badge";

export default function AnalyticsPage() {
  const connectorHealth = [
    { name: "Slack", pct: 99.98, color: "#611f69" },
    { name: "Stripe", pct: 99.99, color: "#635BFF" },
    { name: "GitHub", pct: 98.4, color: "#24292F" },
    { name: "Gmail", pct: 99.7, color: "#EA4335" },
    { name: "Airtable", pct: 99.9, color: "#18BFFF" },
  ];

  return (
    <div className="space-y-8">
      <PageHeader title="Analytics" description="Usage, latency, cost, and reliability across your workspace.">
        <Select defaultValue="30d">
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
        <Card>
          <CardHeader>
            <CardTitle>Connector health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {connectorHealth.map((c) => (
              <div key={c.name} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{c.name}</span>
                  <span className="text-muted-foreground tabular-nums">{c.pct.toFixed(2)}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all duration-1000"
                    style={{ width: `${c.pct / 100 * 100}%`, background: c.color }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent executions</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {executions.slice(0, 5).map((ex) => (
              <div key={ex.id} className="flex items-center gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{ex.workflowName}</p>
                  <p className="text-xs text-muted-foreground">{ex.triggeredBy} · attempt {ex.attempts}</p>
                </div>
                {ex.error && <p className="hidden max-w-[40%] truncate font-mono text-[11px] text-destructive lg:block">{ex.error}</p>}
                <StatusBadge status={ex.status} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Failure distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Rate limit (429)", pct: 42 },
              { label: "Auth expired", pct: 27 },
              { label: "Network timeout", pct: 18 },
              { label: "Invalid payload", pct: 13 },
            ].map((f) => (
              <div key={f.label}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{f.label}</span>
                  <span className="tabular-nums">{f.pct}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-gradient-to-r from-brand-purple to-brand-cyan" style={{ width: `${f.pct}%` }} />
                </div>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-2">
              <Badge variant="warning">1 incident this month</Badge>
              <Badge variant="secondary">P95 latency 1.8s</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
