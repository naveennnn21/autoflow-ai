"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  CheckCircle2,
  CircleDashed,
  Clock,
  ListOrdered,
  Loader2,
  Pause,
  Terminal,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type RunEntryStatus = "waiting" | "running" | "completed" | "failed";

export interface RunEntry {
  id: string;
  nodeId: string;
  nodeName: string;
  status: RunEntryStatus;
  time: string; // ISO timestamp
  error?: string | null;
  attempts?: number;
  durationMs?: number;
}

export type RunPhase =
  | "idle"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

const PHASE_META: Record<RunPhase, { label: string; className: string; pulse?: boolean }> = {
  idle: { label: "Not started", className: "bg-muted text-muted-foreground" },
  running: {
    label: "Running",
    className: "bg-primary/15 text-primary",
    pulse: true,
  },
  paused: { label: "Paused", className: "bg-warning/15 text-warning" },
  completed: { label: "Completed", className: "bg-success/15 text-success" },
  failed: { label: "Failed", className: "bg-destructive/15 text-destructive" },
  cancelled: { label: "Cancelled", className: "bg-muted text-muted-foreground" },
};

const STATUS_ICON = {
  waiting: CircleDashed,
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
} as const;

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function StatusIcon({ status }: { status: RunEntryStatus }) {
  const Icon = STATUS_ICON[status];
  return (
    <span
      className={cn(
        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
        status === "completed" && "bg-success/15 text-success",
        status === "failed" && "bg-destructive/15 text-destructive",
        status === "running" && "bg-primary/15 text-primary",
        status === "waiting" && "bg-muted text-muted-foreground",
      )}
    >
      <Icon className={cn("h-3 w-3", status === "running" && "animate-spin")} />
    </span>
  );
}

interface ExecutionPanelProps {
  open: boolean;
  onToggle: (open: boolean) => void;
  entries: RunEntry[];
  phase: RunPhase;
  error?: string | null;
  onClear: () => void;
}

export function ExecutionPanel({
  open,
  onToggle,
  entries,
  phase,
  error,
  onClear,
}: ExecutionPanelProps) {
  const meta = PHASE_META[phase];

  const stats = React.useMemo(() => {
    const counts: Record<RunEntryStatus, number> = {
      waiting: 0,
      running: 0,
      completed: 0,
      failed: 0,
    };
    let totalMs = 0;
    let retries = 0;
    const latest = new Map<string, RunEntry>();
    for (const entry of entries) {
      latest.set(entry.nodeId, entry);
      if (entry.durationMs) totalMs += entry.durationMs;
      if ((entry.attempts ?? 1) > 1) retries += 1;
    }
    for (const entry of latest.values()) counts[entry.status] += 1;
    return { ...counts, totalMs, retries };
  }, [entries]);

  const logLines = React.useMemo(
    () =>
      entries.map((entry) => {
        const time = fmtTime(entry.time);
        if (entry.status === "running") {
          return { id: entry.id, level: "info" as const, text: `[${time}] ${entry.nodeName} started` };
        }
        if (entry.status === "completed") {
          const dur = entry.durationMs ? ` (${entry.durationMs}ms)` : "";
          const retries = (entry.attempts ?? 1) > 1 ? ` after ${entry.attempts} attempts` : "";
          return { id: entry.id, level: "ok" as const, text: `[${time}] ${entry.nodeName} completed${dur}${retries}` };
        }
        if (entry.status === "failed") {
          return {
            id: entry.id,
            level: "error" as const,
            text: `[${time}] ${entry.nodeName} failed: ${entry.error ?? "unknown error"}`,
          };
        }
        return { id: entry.id, level: "muted" as const, text: `[${time}] ${entry.nodeName} waiting` };
      }),
    [entries],
  );

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 260, damping: 26 }}
          className="absolute bottom-4 right-4 z-20 flex max-h-[70%] w-[380px] max-w-[calc(100%-2rem)] flex-col overflow-hidden rounded-2xl border border-border bg-card/95 shadow-soft-lg backdrop-blur-xl"
        >
          {/* Header */}
          <div className="flex items-center gap-2 border-b border-border/60 px-3.5 py-2.5">
            <span className={cn("relative flex h-2 w-2", meta.pulse && "text-primary")}>
              {meta.pulse && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
              )}
              <span
                className={cn(
                  "relative inline-flex h-2 w-2 rounded-full",
                  phase === "running" && "bg-primary shadow-[0_0_8px_hsl(var(--primary))]",
                  phase === "completed" && "bg-success",
                  phase === "failed" && "bg-destructive",
                  phase === "paused" && "bg-warning",
                  (phase === "idle" || phase === "cancelled") && "bg-muted-foreground",
                )}
              />
            </span>
            <span className="text-sm font-semibold tracking-tight">Live execution</span>
            <Badge variant="outline" className={cn("ml-auto gap-1 text-[10px]", meta.className)}>
              {phase === "paused" && <Pause className="h-2.5 w-2.5" />}
              {meta.label}
            </Badge>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-6 w-6"
              aria-label="Clear run logs"
              onClick={onClear}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-6 w-6"
              aria-label="Close execution panel"
              onClick={() => onToggle(false)}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>

          {error && (
            <div className="mx-3.5 mt-2.5 flex items-start gap-1.5 rounded-lg border border-destructive/25 bg-destructive/5 px-2.5 py-2 text-xs text-destructive">
              <XCircle className="mt-0.5 h-3 w-3 shrink-0" />
              {error}
            </div>
          )}

          <Tabs defaultValue="timeline" className="flex min-h-0 flex-1 flex-col px-3.5 pt-2.5">
            <TabsList className="w-full">
              <TabsTrigger value="timeline" className="flex-1 gap-1.5 text-xs">
                <Activity className="h-3.5 w-3.5" /> Timeline
              </TabsTrigger>
              <TabsTrigger value="logs" className="flex-1 gap-1.5 text-xs">
                <Terminal className="h-3.5 w-3.5" /> Logs
              </TabsTrigger>
              <TabsTrigger value="metrics" className="flex-1 gap-1.5 text-xs">
                <ListOrdered className="h-3.5 w-3.5" /> Metrics
              </TabsTrigger>
            </TabsList>

            {/* Timeline */}
            <TabsContent value="timeline" className="min-h-0 flex-1 overflow-y-auto pb-2 no-scrollbar">
              {entries.length === 0 ? (
                <EmptyRunState />
              ) : (
                <ol className="relative space-y-1 pt-1">
                  {entries.map((entry, i) => {
                    const isLast = i === entries.length - 1;
                    return (
                      <li key={entry.id} className="relative flex gap-2.5">
                        {!isLast && (
                          <span className="absolute left-[9px] top-5 bottom-[-4px] w-px bg-border/60" />
                        )}
                        <StatusIcon status={entry.status} />
                        <div className="min-w-0 flex-1 pb-2.5">
                          <div className="flex items-baseline justify-between gap-2">
                            <p className="truncate text-xs font-medium">{entry.nodeName}</p>
                            <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                              {fmtTime(entry.time)}
                            </span>
                          </div>
                          <p className="mt-0.5 text-[11px] capitalize text-muted-foreground">
                            {entry.status}
                            {entry.durationMs ? ` · ${entry.durationMs}ms` : ""}
                            {(entry.attempts ?? 1) > 1 ? ` · ${entry.attempts} attempts` : ""}
                          </p>
                          {entry.error && (
                            <p className="mt-0.5 truncate text-[11px] text-destructive" title={entry.error}>
                              {entry.error}
                            </p>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </TabsContent>

            {/* Logs */}
            <TabsContent value="logs" className="min-h-0 flex-1 overflow-y-auto pb-2 no-scrollbar">
              {logLines.length === 0 ? (
                <EmptyRunState />
              ) : (
                <div className="space-y-1 rounded-lg border border-border/50 bg-background/60 p-2.5 font-mono text-[11px] leading-relaxed">
                  {logLines.map((line) => (
                    <p
                      key={line.id}
                      className={cn(
                        "break-all",
                        line.level === "error" && "text-destructive",
                        line.level === "ok" && "text-success",
                        line.level === "info" && "text-primary",
                        line.level === "muted" && "text-muted-foreground",
                      )}
                    >
                      {line.text}
                    </p>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Metrics */}
            <TabsContent value="metrics" className="min-h-0 flex-1 overflow-y-auto pb-2 no-scrollbar">
              {entries.length === 0 ? (
                <EmptyRunState />
              ) : (
                <div className="grid grid-cols-2 gap-2 pb-1">
                  <MetricCard label="Completed" value={stats.completed} tone="success" />
                  <MetricCard label="Failed" value={stats.failed} tone="destructive" />
                  <MetricCard label="Running" value={stats.running} tone="primary" />
                  <MetricCard label="Waiting" value={stats.waiting} tone="muted" />
                  <MetricCard
                    label="Total duration"
                    value={stats.totalMs >= 1000 ? `${(stats.totalMs / 1000).toFixed(1)}s` : `${Math.round(stats.totalMs)}ms`}
                    tone="neutral"
                  />
                  <MetricCard label="Retries" value={stats.retries} tone="neutral" />
                </div>
              )}
            </TabsContent>
          </Tabs>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone: "success" | "destructive" | "primary" | "muted" | "neutral";
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/50 px-3 py-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-0.5 text-lg font-semibold tabular-nums",
          tone === "success" && "text-success",
          tone === "destructive" && "text-destructive",
          tone === "primary" && "text-primary",
          tone === "muted" && "text-muted-foreground",
          tone === "neutral" && "text-foreground",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function EmptyRunState() {
  return (
    <div className="flex h-full min-h-24 flex-col items-center justify-center gap-2 text-center">
      <Clock className="h-5 w-5 text-muted-foreground/40" />
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        Press <span className="font-medium text-foreground">Run</span> to stream
        live node events here.
      </p>
    </div>
  );
}
