"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Heart, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatDuration, timeAgo } from "@/lib/utils";
import type { Workflow } from "@/types";
import { useWorkflows } from "@/stores/workflows";

export function WorkflowCard({ workflow }: { workflow: Workflow }) {
  const { toggleFavorite, removeWorkflow } = useWorkflows();
  const statusVariant = {
    active: "success",
    draft: "secondary",
    paused: "warning",
    archived: "default",
    failed: "destructive",
  }[workflow.status] as "success" | "secondary" | "warning" | "default" | "destructive";

  const onToggleFavorite = async () => {
    try {
      await toggleFavorite(workflow.id);
    } catch {
      toast.error("Could not update favorite", { description: "The workflow API is unreachable." });
    }
  };

  const onDelete = async () => {
    try {
      await removeWorkflow(workflow.id);
      toast.success(`Deleted "${workflow.name}"`);
    } catch {
      toast.error("Could not delete workflow");
    }
  };

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 400, damping: 30 }}>
      <Card className="card-hover group h-full overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-2">
            <Badge variant={statusVariant} className="capitalize">{workflow.status}</Badge>
            <div className="flex items-center gap-0.5">
              <button
                onClick={() => void onToggleFavorite()}
                className="rounded-full p-1 text-muted-foreground transition-colors hover:text-rose-500"
                aria-label="Toggle favorite"
              >
                <Heart className={cn("h-4 w-4 transition-colors", workflow.favorite && "fill-rose-500 text-rose-500")} />
              </button>
              <button
                onClick={() => void onDelete()}
                className="rounded-full p-1 text-muted-foreground transition-colors hover:text-destructive"
                aria-label="Delete workflow"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <h3 className="mt-3 font-semibold leading-snug">{workflow.name}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{workflow.description}</p>

          <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Play className="h-3 w-3" /> {workflow.runs.toLocaleString()} runs</span>
            {workflow.successRate > 0 && <span className="text-success">{workflow.successRate}% success</span>}
            <span className="ml-auto">{workflow.avgDurationMs ? formatDuration(workflow.avgDurationMs) : "—"}</span>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
            <span className="text-[11px] text-muted-foreground">
              <span suppressHydrationWarning>{workflow.lastRunAt ? `Ran ${timeAgo(workflow.lastRunAt)}` : "Never run"}</span>
            </span>
            <Link
              href={`/workflows/${workflow.id}/builder`}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary transition-colors hover:underline"
            >
              Open builder
              <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
