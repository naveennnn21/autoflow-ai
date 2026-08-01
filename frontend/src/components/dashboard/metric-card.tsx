"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { CountUp } from "@/components/motion/count-up";
import { cn } from "@/lib/utils";
import type { Metric } from "@/types";

export function MetricCard({ metric }: { metric: Metric }) {
  const positive = metric.delta >= 0;
  const good = metric.id === "latency" ? !positive : positive;

  return (
    <Card className="card-hover group relative overflow-hidden border-border/70 shadow-[inset_0_1px_0_0_hsl(var(--foreground)/0.04)]">
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl transition-opacity group-hover:opacity-100 opacity-0" />
      <CardContent className="p-5">
        <div aria-hidden className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" />
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{metric.label}</p>
        <div className="mt-2 flex items-baseline gap-2">
          <CountUp
            value={metric.value}
            decimals={metric.format === "percent" ? 1 : 0}
            prefix={metric.format === "currency" ? "$" : metric.unit === "$" ? "$" : ""}
            suffix={metric.unit === "%" || metric.format === "percent" ? "%" : metric.format === "currency" ? "" : metric.unit ?? ""}
            className="text-2xl font-bold tracking-tight"
          />
          <span className={cn("inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-medium", good ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive")}>
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(metric.delta)}%
          </span>
        </div>
        <div className="mt-3 flex h-8 items-end gap-0.5">
          {metric.spark.map((v, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm bg-gradient-to-t from-primary/30 to-primary/70 transition-all"
              style={{ height: `${(v / Math.max(...metric.spark)) * 100}%` }}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
