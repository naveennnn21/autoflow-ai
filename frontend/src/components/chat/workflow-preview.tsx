"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Rocket, Sparkles, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/shared/icons";
import { aiWorkflowApi } from "@/lib/api/ai-workflow";
import { workflowsApi } from "@/lib/api/workflows";
import { useWorkflows } from "@/stores/workflows";
import type { WorkflowPreview } from "@/types";

const phaseLabels = ["Compiling workflow spec", "Validating graph", "Deploying"];

export function WorkflowPreviewCard({ preview }: { preview: WorkflowPreview }) {
  const router = useRouter();
  const [phase, setPhase] = React.useState<number | null>(null);
  const [done, setDone] = React.useState(false);
  const [deploying, setDeploying] = React.useState(false);
  const [warnings, setWarnings] = React.useState<string[]>([]);
  const [workflowId, setWorkflowId] = React.useState<string | null>(null);
  const [deployedVersion, setDeployedVersion] = React.useState<number | null>(null);

  const deploy = async () => {
    if (deploying) return;
    setDeploying(true);
    setPhase(0);
    setDone(false);
    setWarnings([]);
    phaseLabels.forEach((_, i) => {
      setTimeout(() => setPhase(i), i * 700);
    });

    try {
      const nodes = preview.steps.map((s, i) => ({
        id: `n${i + 1}`,
        kind: (i === 0 ? "trigger" : "action") as "trigger" | "action",
        label: s.label,
        connector: s.connector,
        action: s.action,
      }));
      const edges = preview.steps.slice(1).map((_, i) => ({
        id: `e${i + 1}`,
        source: `n${i + 1}`,
        target: `n${i + 2}`,
      }));

      const result = await aiWorkflowApi.deploy(
        { name: preview.name, nodes, edges },
        workflowId ?? undefined,
        preview.description,
      );

      if (!result.ok || !result.workflow_id) {
        setWarnings(result.errors ?? []);
        toast.error("Deploy failed", {
          description: (result.errors ?? []).join(" ") || "The workflow did not pass validation.",
        });
        return;
      }

      setWorkflowId(result.workflow_id);
      setDeployedVersion(result.version ?? null);
      if (result.warnings?.length) setWarnings(result.warnings);
      try {
        const workflow = await workflowsApi.get(result.workflow_id);
        useWorkflows.getState().addWorkflow(workflow);
      } catch {
        // workflow list refresh is best-effort
      }
      setDone(true);
      toast.success("Workflow deployed", {
        description: `v${result.version ?? 1} is live and ready to execute.`,
        action: {
          label: "Open builder",
          onClick: () => router.push(`/workflows/${result.workflow_id}/builder`),
        },
      });
    } catch (err) {
      const detail = err instanceof Error ? err.message : "The workflow API is unreachable.";
      setWarnings([detail]);
      toast.error("Deploy failed", { description: detail });
    } finally {
      setDeploying(false);
      setTimeout(() => setPhase(null), 600);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 24 }}
      className="gradient-border overflow-hidden rounded-2xl bg-card"
    >
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <div>
              <p className="text-sm font-semibold leading-tight">{preview.name}</p>
              <p className="text-xs text-muted-foreground">{preview.description}</p>
            </div>
          </div>
          <AnimatePresence>
            {done ? (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="flex items-center gap-1 rounded-full bg-success/15 px-2.5 py-1 text-xs font-medium text-success"
              >
                <Check className="h-3 w-3" /> Created
              </motion.span>
            ) : (
              <motion.span
                key="ready"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground"
              >
                {deploying ? "Deploying…" : "Ready to deploy"}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-3 no-scrollbar">
          {preview.steps.map((step, i) => (
            <React.Fragment key={step.label}>
              {i > 0 && <div className="h-px w-5 shrink-0 bg-border" />}
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.1 }}
                className="flex shrink-0 flex-col items-center gap-1"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-background/60">
                  <Icon name={step.connector} className="h-4 w-4" />
                </span>
                <span className="text-[10px] font-medium text-muted-foreground">{step.label}</span>
              </motion.div>
            </React.Fragment>
          ))}
        </div>

        {warnings.length > 0 && (
          <div className="mt-3 space-y-1 rounded-xl border border-amber-500/25 bg-amber-500/5 px-3 py-2">
            {warnings.map((w) => (
              <div key={w} className="flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
                {w}
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-border bg-background/40 px-3 py-2">
          <span className="text-xs text-muted-foreground">{preview.estimate}</span>
          <div className="flex gap-2">
            {done && workflowId && (
              <span className="hidden items-center gap-1 rounded-full bg-success/10 px-2 py-1 text-[10px] font-medium text-success sm:flex">
                v{deployedVersion ?? 1} · {workflowId.slice(0, 8)}
              </span>
            )}
            {phase !== null && (
              <motion.span
                key={phase}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-1.5 text-xs font-medium text-primary"
              >
                <span className="h-2 w-2 animate-ping rounded-full bg-primary" />
                {phaseLabels[phase]}
              </motion.span>
            )}
            <Button size="sm" variant={done ? "secondary" : "default"} onClick={() => void deploy()} disabled={deploying}>
              {done ? (
                <>
                  <Check className="h-3.5 w-3.5" /> Deploy again
                </>
              ) : (
                <>
                  <Rocket className="h-3.5 w-3.5" /> Deploy
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
