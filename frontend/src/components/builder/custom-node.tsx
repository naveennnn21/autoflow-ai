"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { CheckCircle2, CircleDashed, Loader2, RefreshCw, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/shared/icons";
import type { ExecutionStatus } from "@/types";

const statusStyles: Record<ExecutionStatus, { ring: string; glow: string; icon: typeof CircleDashed }> = {
  waiting: { ring: "border-border/70", glow: "", icon: CircleDashed },
  running: { ring: "border-primary/70", glow: "shadow-[0_0_28px_-6px_hsl(var(--primary)/0.55)]", icon: Loader2 },
  retrying: { ring: "border-warning/70", glow: "shadow-[0_0_28px_-6px_hsl(var(--warning)/0.55)]", icon: RefreshCw },
  success: { ring: "border-success/70", glow: "shadow-[0_0_28px_-6px_hsl(var(--success)/0.55)]", icon: CheckCircle2 },
  failed: { ring: "border-destructive/70", glow: "shadow-[0_0_28px_-6px_hsl(var(--destructive)/0.55)]", icon: XCircle },
  rollback: { ring: "border-warning/70", glow: "", icon: RefreshCw },
  paused: { ring: "border-border/70", glow: "", icon: CircleDashed },
};

export const CustomNode = memo(({ data, selected }: NodeProps) => {
  const d = data as {
    label: string;
    kind: string;
    connector?: string;
    status?: ExecutionStatus;
  };
  const status = d.status ?? "waiting";
  const s = statusStyles[status];
  const StatusIcon = s.icon;

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className={cn(
        "relative min-w-[170px] rounded-xl border bg-card/95 p-3 shadow-[inset_0_1px_0_0_hsl(var(--foreground)/0.05),0_8px_24px_-12px_rgba(0,0,0,0.5)] backdrop-blur-xl transition-shadow",
        s.ring,
        s.glow,
        selected && "ring-2 ring-ring",
      )}
    >
      <Handle type="target" position={Position.Top} className="!h-2.5 !w-2.5 !border-0 !bg-border shadow-[0_0_6px_hsl(var(--primary)/0.6)]" />
      <div className="flex items-center gap-2.5">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-shadow",
            d.kind === "trigger" && "bg-success/15 text-success shadow-[0_0_12px_-4px_hsl(var(--success)/0.5)]",
            d.kind === "ai" && "bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-[0_0_12px_-4px_hsl(var(--primary)/0.5)]",
            d.kind === "condition" && "bg-warning/15 text-warning shadow-[0_0_12px_-4px_hsl(var(--warning)/0.5)]",
            d.kind === "action" && "bg-primary/15 text-primary shadow-[0_0_12px_-4px_hsl(var(--primary)/0.5)]",
          )}
        >
          {d.kind === "ai" ? <Icon name="brain" className="h-4 w-4" /> : <Icon name={d.connector ?? "zap"} className="h-4 w-4" />}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium leading-tight">{d.label}</p>
          <p className="truncate text-[11px] text-muted-foreground capitalize">{d.kind}</p>
        </div>
        <span
          className={cn(
            "ml-auto flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
            status === "success" && "text-success",
            status === "failed" && "text-destructive",
            status === "retrying" && "text-warning",
            status === "running" && "text-primary",
            (status === "waiting" || status === "paused") && "text-muted-foreground",
          )}
        >
          {status === "running" ? <StatusIcon className="h-4 w-4 animate-spin" /> : <StatusIcon className="h-4 w-4" />}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5 !border-0 !bg-border shadow-[0_0_6px_hsl(var(--primary)/0.6)]" />
    </motion.div>
  );
});

CustomNode.displayName = "CustomNode";
