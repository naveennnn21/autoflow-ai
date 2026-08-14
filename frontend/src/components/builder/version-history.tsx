"use client";

import * as React from "react";
import {
  ChevronDown,
  GitCompareArrows,
  History,
  MinusCircle,
  PlusCircle,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  aiWorkflowApi,
  type DiffResult,
  type VersionSnapshot,
} from "@/lib/api/ai-workflow";
import { executionsApi } from "@/lib/api/executions";
import type { Execution } from "@/types";

function fmtDate(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString([], { hour12: false });
  } catch {
    return iso;
  }
}

const RUN_TONE: Record<string, string> = {
  success: "bg-success/15 text-success",
  failed: "bg-destructive/15 text-destructive",
  running: "bg-primary/15 text-primary",
  retrying: "bg-warning/15 text-warning",
  waiting: "bg-muted text-muted-foreground",
  paused: "bg-warning/15 text-warning",
  cancelled: "bg-muted text-muted-foreground",
};

interface VersionHistoryProps {
  workflowId: string;
  open: boolean;
  onClose: () => void;
  onRestored?: () => void;
}

export function VersionHistory({ workflowId, open, onClose, onRestored }: VersionHistoryProps) {
  const [versions, setVersions] = React.useState<VersionSnapshot[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [runs, setRuns] = React.useState<Execution[]>([]);
  const [runsLoading, setRunsLoading] = React.useState(false);
  const [expanded, setExpanded] = React.useState<number | null>(null);
  const [fromVer, setFromVer] = React.useState("");
  const [toVer, setToVer] = React.useState("");
  const [diff, setDiff] = React.useState<DiffResult | null>(null);
  const [diffing, setDiffing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [restoring, setRestoring] = React.useState<number | null>(null);
  const [restoreResult, setRestoreResult] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRestoreResult(null);
    aiWorkflowApi
      .versions(workflowId)
      .then((res) => {
        if (cancelled) return;
        setVersions(res.versions);
        const nums = res.versions.map((v) => String(v.version));
        if (nums.length >= 2) {
          setFromVer(nums[0]);
          setToVer(nums[1]);
        } else if (nums.length === 1) {
          setFromVer(nums[0]);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load versions");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    setRunsLoading(true);
    executionsApi
      .list({ page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) {
          setRuns(res.items.filter((r) => r.workflowId === workflowId).slice(0, 25));
        }
      })
      .catch(() => {
        /* runs are best-effort */
      })
      .finally(() => {
        if (!cancelled) setRunsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, workflowId]);

  const restoreVersion = async (version: number) => {
    if (!workflowId) return;
    setRestoring(version);
    try {
      const res = await aiWorkflowApi.restore(workflowId, version);
      setRestoreResult(
        `v${version} restored as v${res.new_version_number} — earlier versions untouched.`,
      );
      const fresh = await aiWorkflowApi.versions(workflowId);
      setVersions(fresh.versions);
      onRestored?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restore version");
    } finally {
      setRestoring(null);
    }
  };

  const runDiff = async () => {
    const from = Number(fromVer);
    const to = Number(toVer);
    if (!from || !to || from === to) return;
    setDiffing(true);
    setDiff(null);
    try {
      setDiff(await aiWorkflowApi.diff(workflowId, from, to));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not diff versions");
    } finally {
      setDiffing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-4 w-4 text-primary" />
            Workflow history
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded-xl border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}
        {restoreResult && (
          <div className="rounded-xl border border-success/25 bg-success/5 px-3 py-2 text-xs text-success">
            {restoreResult}
          </div>
        )}

        <Tabs defaultValue="versions">
          <TabsList className="w-full">
            <TabsTrigger value="versions" className="flex-1 gap-1.5 text-xs">
              <GitCompareArrows className="h-3.5 w-3.5" /> Versions · Diff
            </TabsTrigger>
            <TabsTrigger value="runs" className="flex-1 gap-1.5 text-xs">
              <RefreshCw className="h-3.5 w-3.5" /> Past runs
            </TabsTrigger>
          </TabsList>

          {/* Versions + diff */}
          <TabsContent value="versions" className="max-h-[55vh] overflow-y-auto no-scrollbar">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Loading versions…
              </div>
            ) : versions.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <History className="h-6 w-6 text-muted-foreground/40" />
                <p className="text-xs text-muted-foreground">
                  No versions yet — deploy this workflow to create version 1.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {versions.map((v) => {
                  const isOpen = expanded === v.version;
                  const nodes = v.definition?.nodes ?? [];
                  return (
                    <div
                      key={v.version}
                      className="overflow-hidden rounded-xl border border-border/60 bg-background/40"
                    >
                      <button
                        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/40"
                        onClick={() => setExpanded(isOpen ? null : (v.version ?? null))}
                      >
                        <Badge variant="gradient" className="gap-1 text-[10px]">
                          v{v.version}
                        </Badge>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium">
                            {nodes.length} nodes · {v.definition?.edges?.length ?? 0} edges
                          </p>
                          <p className="text-[10px] text-muted-foreground">
                            {fmtDate(v.created_at)}
                            {v.compiler_version ? ` · compiler ${v.compiler_version}` : ""}
                            {v.planner_version ? ` · planner ${v.planner_version}` : ""}
                          </p>
                        </div>
                        <ChevronDown
                          className={cn(
                            "h-3.5 w-3.5 text-muted-foreground transition-transform",
                            isOpen && "rotate-180",
                          )}
                        />
                      </button>
                      {isOpen && (
                        <div className="border-t border-border/50 px-3 py-2.5">
                          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                            Nodes
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {nodes.length === 0 ? (
                              <span className="text-[11px] text-muted-foreground">
                                No node snapshot stored.
                              </span>
                            ) : (
                              nodes.map((n) => (
                                <span
                                  key={n.id}
                                  className="rounded-full border border-border bg-card px-2 py-0.5 text-[10px] text-muted-foreground"
                                >
                                  {n.label ?? n.id}
                                </span>
                              ))
                            )}
                          </div>
                          {v.spec && (
                            <pre className="mt-2 max-h-40 overflow-auto rounded-lg border border-border/50 bg-background/60 p-2.5 text-[10px] leading-relaxed text-muted-foreground no-scrollbar">
                              {JSON.stringify(v.spec, null, 2).slice(0, 4000)}
                            </pre>
                          )}
                          <div className="mt-2.5 flex flex-wrap items-center gap-2">
                            {restoring === v.version ? (
                              <>
                                <span className="text-[11px] text-muted-foreground">
                                  Create v
                                  {versions.reduce((m, x) => Math.max(m, x.version ?? 0), 0) + 1}{" "}
                                  from v{v.version}?
                                </span>
                                <Button
                                  size="sm"
                                  className="h-7 gap-1 text-xs"
                                  onClick={() => void restoreVersion(v.version)}
                                >
                                  <RotateCcw className="h-3 w-3" />
                                  Confirm
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 text-xs"
                                  onClick={() => setRestoring(null)}
                                >
                                  Cancel
                                </Button>
                              </>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 text-xs"
                                disabled={restoring !== null}
                                onClick={() => setRestoring(v.version)}
                              >
                                <RotateCcw className="h-3 w-3" />
                                Restore version
                              </Button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Diff */}
                {versions.length >= 2 && (
                  <div className="mt-3 rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Compare versions
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Select value={fromVer} onValueChange={setFromVer}>
                        <SelectTrigger className="h-8 w-24 text-xs">
                          <SelectValue placeholder="From" />
                        </SelectTrigger>
                        <SelectContent>
                          {versions.map((v) => (
                            <SelectItem key={v.version} value={String(v.version)}>
                              v{v.version}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <span className="text-[11px] text-muted-foreground">→</span>
                      <Select value={toVer} onValueChange={setToVer}>
                        <SelectTrigger className="h-8 w-24 text-xs">
                          <SelectValue placeholder="To" />
                        </SelectTrigger>
                        <SelectContent>
                          {versions.map((v) => (
                            <SelectItem key={v.version} value={String(v.version)}>
                              v{v.version}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 gap-1.5 text-xs"
                        onClick={() => void runDiff()}
                        disabled={diffing || !fromVer || !toVer || fromVer === toVer}
                      >
                        <GitCompareArrows className="h-3.5 w-3.5" />
                        Diff
                      </Button>
                    </div>
                    {diff && (
                      <div className="mt-2.5 grid grid-cols-2 gap-2">
                        <div className="rounded-lg border border-success/20 bg-success/5 px-2.5 py-2">
                          <p className="mb-1 flex items-center gap-1 text-[10px] font-medium text-success">
                            <PlusCircle className="h-3 w-3" /> Added in v{diff.to_version}
                          </p>
                          {diff.added_nodes.length === 0 ? (
                            <p className="text-[10px] text-muted-foreground">None</p>
                          ) : (
                            diff.added_nodes.map((id) => (
                              <p key={id} className="text-[10px] text-muted-foreground">
                                {id}
                              </p>
                            ))
                          )}
                        </div>
                        <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-2.5 py-2">
                          <p className="mb-1 flex items-center gap-1 text-[10px] font-medium text-destructive">
                            <MinusCircle className="h-3 w-3" /> Removed
                          </p>
                          {diff.removed_nodes.length === 0 ? (
                            <p className="text-[10px] text-muted-foreground">None</p>
                          ) : (
                            diff.removed_nodes.map((id) => (
                              <p key={id} className="text-[10px] text-muted-foreground">
                                {id}
                              </p>
                            ))
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          {/* Past runs */}
          <TabsContent value="runs" className="max-h-[55vh] overflow-y-auto no-scrollbar">
            {runsLoading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Loading runs…
              </div>
            ) : runs.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <RefreshCw className="h-6 w-6 text-muted-foreground/40" />
                <p className="text-xs text-muted-foreground">
                  No executions yet — press Run in the builder to create one.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {runs.map((run) => (
                  <div
                    key={run.id}
                    className="flex items-center gap-3 rounded-xl border border-border/60 bg-background/40 px-3 py-2"
                  >
                    <span
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        run.status === "success" && "bg-success",
                        run.status === "failed" && "bg-destructive",
                        run.status === "running" && "bg-primary animate-pulse",
                        (run.status === "waiting" || run.status === "cancelled") && "bg-muted-foreground",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">
                        {run.id.slice(0, 18)}
                        <span className="ml-1.5 text-[10px] font-normal text-muted-foreground">
                          {run.triggeredBy}
                        </span>
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        {fmtDate(run.startedAt)}
                        {run.durationMs != null ? ` · ${run.durationMs}ms` : ""}
                        {run.attempts > 1 ? ` · ${run.attempts} attempts` : ""}
                      </p>
                    </div>
                    <Badge variant="outline" className={cn("text-[10px]", RUN_TONE[run.status] ?? "bg-muted text-muted-foreground")}>
                      {run.status}
                    </Badge>
                    {run.error && (
                      <span className="hidden max-w-40 truncate text-[10px] text-destructive sm:block" title={run.error}>
                        {run.error}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
