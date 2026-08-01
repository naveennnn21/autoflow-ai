"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  PauseCircle,
  RefreshCw,
  Undo2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ExecutionStatus } from "@/types";

const config: Record<
  ExecutionStatus,
  { label: string; variant: "success" | "destructive" | "warning" | "info" | "secondary" | "default"; icon: typeof CheckCircle2 }
> = {
  waiting: { label: "Waiting", variant: "secondary", icon: Clock },
  running: { label: "Running", variant: "info", icon: Loader2 },
  retrying: { label: "Retrying", variant: "warning", icon: RefreshCw },
  success: { label: "Success", variant: "success", icon: CheckCircle2 },
  failed: { label: "Failed", variant: "destructive", icon: XCircle },
  rollback: { label: "Rollback", variant: "warning", icon: Undo2 },
  paused: { label: "Paused", variant: "secondary", icon: PauseCircle },
};

export function StatusBadge({ status }: { status: ExecutionStatus }) {
  const c = config[status];
  const IconComp = c.icon;
  return (
    <Badge variant={c.variant}>
      <IconComp className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />
      {c.label}
    </Badge>
  );
}

export function ConnectorHealthBadge({ health }: { health: "healthy" | "degraded" | "down" }) {
  if (health === "healthy") return <Badge variant="success">Healthy</Badge>;
  if (health === "degraded") return <Badge variant="warning">Degraded</Badge>;
  return (
    <Badge variant="destructive">
      <AlertTriangle className="h-3 w-3" /> Down
    </Badge>
  );
}
