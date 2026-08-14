"use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  History,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Rocket,
  Save,
  ShieldCheck,
  Sparkles,
  Square,
  Undo2,
  Redo2,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { FlowCanvas, type FlowCanvasHandle, type RunEvent } from "@/components/builder/flow-canvas";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { workflowsApi } from "@/lib/api/workflows";
import { aiWorkflowApi, type AiDefinition, type ValidateResult } from "@/lib/api/ai-workflow";
import { toBackendConfig } from "@/lib/api/mappers";
import { cn } from "@/lib/utils";

export default function BuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [id, setId] = React.useState<string | null>(null);
  const canvasRef = React.useRef<FlowCanvasHandle>(null);
  const queryClient = useQueryClient();
  const [saving, setSaving] = React.useState(false);
  const [validating, setValidating] = React.useState(false);
  const [deploying, setDeploying] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [paused, setPaused] = React.useState(false);
  const [executionId, setExecutionId] = React.useState<string | null>(null);
  const [validation, setValidation] = React.useState<ValidateResult | null>(null);
  const [versionCount, setVersionCount] = React.useState(0);
  const abortRef = React.useRef<(() => void) | null>(null);

  React.useEffect(() => {
    void params.then((p) => setId(p.id));
  }, [params]);

  const { data: workflow, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.workflow(id ?? ""),
    queryFn: () => workflowsApi.get(id ?? ""),
    enabled: !!id,
  });

  React.useEffect(() => {
    if (!workflow) return;
    void aiWorkflowApi
      .versions(workflow.id)
      .then((res) => setVersionCount(res.versions.length))
      .catch(() => setVersionCount(0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow?.id]);

  React.useEffect(() => {
    return () => abortRef.current?.();
  }, []);

  const buildDefinition = (): AiDefinition => {
    const snap = canvasRef.current?.getSnapshot();
    return {
      name: workflow?.name ?? "workflow",
      nodes: snap?.nodes ?? workflow?.nodes ?? [],
      edges: snap?.edges ?? workflow?.edges ?? [],
    };
  };

  const saveDraft = async () => {
    if (!workflow) return;
    setSaving(true);
    try {
      const snap = canvasRef.current?.getSnapshot();
      const updated = await workflowsApi.update(workflow.id, {
        config: {
          ...toBackendConfig(workflow),
          nodes: snap?.nodes ?? workflow.nodes,
          edges: snap?.edges ?? workflow.edges,
        },
      });
      queryClient.setQueryData(queryKeys.workflow(workflow.id), updated);
      toast.success("Draft saved", { description: `"${updated.name}" is up to date.` });
    } catch (err) {
      toast.error("Could not save draft", {
        description: err instanceof Error ? err.message : "The workflow API is unreachable.",
      });
    } finally {
      setSaving(false);
    }
  };

  const validate = async () => {
    if (!workflow) return;
    setValidating(true);
    setValidation(null);
    try {
      const result = await aiWorkflowApi.validate(buildDefinition());
      setValidation(result);
      if (result.valid) {
        toast.success("Workflow is valid", {
          description: `${result.node_count} nodes · ${result.edge_count} edges — ready to deploy.`,
        });
      } else {
        toast.error("Validation found issues", {
          description: result.errors[0] ?? "Fix the errors before deploying.",
        });
      }
    } catch (err) {
      toast.error("Validation failed", {
        description: err instanceof Error ? err.message : "The validation API is unreachable.",
      });
    } finally {
      setValidating(false);
    }
  };

  const deploy = async () => {
    if (!workflow) return;
    setDeploying(true);
    try {
      const result = await aiWorkflowApi.deploy(buildDefinition(), workflow.id, workflow.description);
      if (!result.ok || !result.workflow_id) {
        toast.error("Deploy failed", {
          description: (result.errors ?? []).join(" ") || "The workflow did not pass validation.",
        });
        if (result.errors?.length) {
          setValidation({ valid: false, errors: result.errors, warnings: result.warnings ?? [], node_count: 0, edge_count: 0 });
        }
        return;
      }
      const updated = await workflowsApi.get(result.workflow_id);
      queryClient.setQueryData(queryKeys.workflow(result.workflow_id), updated);
      setVersionCount((c) => c + 1);
      toast.success("Workflow deployed", {
        description: `v${result.version ?? 1} is live. It won't execute until you press Run.`,
      });
    } catch (err) {
      toast.error("Deploy failed", {
        description: err instanceof Error ? err.message : "The workflow API is unreachable.",
      });
    } finally {
      setDeploying(false);
    }
  };

  const testRun = async () => {
    if (!workflow || running) return;
    setRunning(true);
    setPaused(false);
    setValidation(null);
    canvasRef.current?.clearRun();
    try {
      const result = await aiWorkflowApi.execute(workflow.id, buildDefinition());
      setExecutionId(result.execution_id);
      toast.success("Execution started", {
        description: `Running "${workflow.name}" through the workflow runtime…`,
      });
      const abort = aiWorkflowApi.streamExecution(result.execution_id, {
        onNode: (event: RunEvent) => canvasRef.current?.applyRunEvent(event),
        onState: (state) => {
          const status = String(state.status ?? "unknown");
          if (status === "completed" || status === "failed" || status === "cancelled") {
            setRunning(false);
            setPaused(false);
            if (status === "completed") {
              toast.success("Execution completed", { description: "All steps finished successfully." });
            } else if (status === "failed") {
              toast.error("Execution failed", {
                description: String(state.error ?? "A step errored — check the node status."),
              });
            } else {
              toast.info("Execution cancelled");
            }
          }
        },
        onError: (err) => {
          setRunning(false);
          toast.error("Execution error", { description: err.message });
        },
        onDone: () => {
          setRunning(false);
          setPaused(false);
        },
      });
      abortRef.current = abort;
    } catch (err) {
      setRunning(false);
      toast.error("Could not start run", {
        description: err instanceof Error ? err.message : "The execution API is unreachable.",
      });
    }
  };

  const cancelRun = async () => {
    if (executionId) {
      try {
        await aiWorkflowApi.control(executionId, "cancel");
        toast.info("Cancelling execution…");
      } catch {
        // fall through - local abort below still stops the stream
      }
    }
    abortRef.current?.();
    abortRef.current = null;
    setRunning(false);
    setPaused(false);
  };

  const togglePause = async () => {
    if (!executionId || !running) return;
    const action = paused ? "resume" : "pause";
    try {
      await aiWorkflowApi.control(executionId, action);
      setPaused((p) => !p);
      toast.info(paused ? "Execution resumed" : "Execution paused");
    } catch (err) {
      toast.error("Could not update run", {
        description: err instanceof Error ? err.message : "The control API is unreachable.",
      });
    }
  };

  const rename = async (name: string) => {
    if (!workflow || !name.trim() || name.trim() === workflow.name) return;
    try {
      const updated = await workflowsApi.update(workflow.id, { name: name.trim() });
      queryClient.setQueryData(queryKeys.workflow(workflow.id), updated);
      toast.success("Workflow renamed");
    } catch (err) {
      toast.error("Could not rename", {
        description: err instanceof Error ? err.message : "The workflow API is unreachable.",
      });
    }
  };

  if (!id || isLoading) {
    return (
      <div className="flex h-[calc(100vh-6.5rem)] flex-col">
        <div className="flex items-center gap-3 pb-4">
          <Skeleton className="h-9 w-9" />
          <div className="space-y-1.5">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-3 w-40" />
          </div>
        </div>
        <Skeleton className="min-h-0 flex-1" />
      </div>
    );
  }

  if (isError || !workflow) {
    if (!isError) notFound();
    return (
      <div className="flex h-[calc(100vh-6.5rem)] flex-col items-center justify-center">
        <EmptyState
          title="Couldn't load this workflow"
          description="The workflow API is unreachable or the workflow was deleted."
          action={
            <Button variant="outline" size="sm" className="gap-2" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col">
      <div className="flex flex-wrap items-center gap-3 pb-4">
        <Button variant="ghost" size="icon-sm" asChild aria-label="Back to workflows">
          <Link href="/workflows">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <input
              defaultValue={workflow.name}
              onBlur={(e) => void rename(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              }}
              className="w-56 truncate rounded-lg border border-transparent bg-transparent px-1.5 py-0.5 text-lg font-semibold tracking-tight outline-none transition-colors hover:border-border focus:border-primary/50 focus:bg-card"
              aria-label="Workflow name"
            />
            <Badge variant={workflow.status === "active" ? "success" : "secondary"}>{workflow.status}</Badge>
            {versionCount > 0 && (
              <Badge variant="outline" className="gap-1">
                <History className="h-3 w-3" /> v{versionCount}
              </Badge>
            )}
          </div>
          <p className="truncate text-xs text-muted-foreground">
            {workflow.nodes.length} nodes · {workflow.edges.length} edges
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button variant="ghost" size="icon-sm" aria-label="Undo"><Undo2 className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon-sm" aria-label="Redo"><Redo2 className="h-4 w-4" /></Button>
          {validation && (
            <span
              className={cn(
                "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                validation.valid
                  ? "bg-success/15 text-success"
                  : "bg-destructive/15 text-destructive",
              )}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {validation.valid ? "Valid" : `${validation.errors.length} issue${validation.errors.length === 1 ? "" : "s"}`}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => void validate()}
            disabled={validating || running}
          >
            {validating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Validate
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void saveDraft()}
            disabled={saving || running}
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save draft
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void deploy()}
            disabled={deploying || running}
          >
            {deploying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
            Deploy
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => router.push("/chat")}>
            <Sparkles className="h-4 w-4" />
            Improve with AI
          </Button>
          {running ? (
            <>
              <Button variant="secondary" size="sm" onClick={() => void togglePause()} disabled={!executionId}>
                {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                {paused ? "Resume" : "Pause"}
              </Button>
              <Button variant="destructive" size="sm" onClick={() => void cancelRun()}>
                <Square className="h-4 w-4" />
                Stop
              </Button>
            </>
          ) : (
            <Button variant="secondary" size="sm" onClick={() => void testRun()}>
              <Play className="h-4 w-4" />
              Run
            </Button>
          )}
        </div>
      </div>

      {validation && !validation.valid && (
        <div className="mb-3 space-y-1 rounded-xl border border-destructive/25 bg-destructive/5 px-3 py-2">
          {validation.errors.slice(0, 4).map((err) => (
            <p key={err} className="text-xs text-destructive">• {err}</p>
          ))}
        </div>
      )}
      {validation?.warnings?.length ? (
        <div className="mb-3 space-y-1 rounded-xl border border-amber-500/25 bg-amber-500/5 px-3 py-2">
          {validation.warnings.slice(0, 4).map((w) => (
            <p key={w} className="text-xs text-amber-600 dark:text-amber-400">• {w}</p>
          ))}
        </div>
      ) : null}

      <div className="min-h-0 flex-1">
        <FlowCanvas key={workflow.id} ref={canvasRef} workflow={workflow} />
      </div>
    </div>
  );
}
