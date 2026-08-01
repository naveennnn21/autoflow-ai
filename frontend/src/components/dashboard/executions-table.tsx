"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatDuration, timeAgo } from "@/lib/utils";
import type { Execution } from "@/types";

export function ExecutionsTable({ executions }: { executions: Execution[] }) {
  return (
    <Card>
      <CardContent className="p-2">
        <div className="divide-y divide-border">
          {executions.map((ex, i) => (
            <motion.div
              key={ex.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-3 px-3 py-3 transition-colors hover:bg-muted/30"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{ex.workflowName}</p>
                <p suppressHydrationWarning className="text-xs text-muted-foreground">
                  {ex.triggeredBy} · {ex.attempts > 1 ? `${ex.attempts} attempts · ` : ""}
                  {ex.durationMs ? formatDuration(ex.durationMs) : timeAgo(ex.startedAt)}
                </p>
              </div>
              <StatusBadge status={ex.status} />
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
