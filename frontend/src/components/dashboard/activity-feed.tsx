"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Plug, Rocket, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { timeAgo } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ActivityItem } from "@/types";

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {items.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
            className="flex gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-muted/40"
          >
            <ActivityIcon type={item.type} status={item.status} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{item.title}</p>
              <p className="truncate text-xs text-muted-foreground">{item.description}</p>
            </div>
            <span suppressHydrationWarning className="shrink-0 text-[11px] text-muted-foreground">{timeAgo(item.timestamp)}</span>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  );
}

function ActivityIcon({ type, status }: { type: ActivityItem["type"]; status?: ActivityItem["status"] }) {
  const cls = cn(
    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
    status === "failed" ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary",
  );
  if (type === "connector") return <div className={cls}><Plug className="h-4 w-4" /></div>;
  if (type === "deploy") return <div className={cls}><Rocket className="h-4 w-4" /></div>;
  if (type === "alert") return <div className={cn(cls, "text-warning bg-warning/10")}><AlertTriangle className="h-4 w-4" /></div>;
  if (type === "user") return <div className={cls}><User className="h-4 w-4" /></div>;
  return (
    <div className={cn(cls, status === "success" && "text-success bg-success/10")}>
      <CheckCircle2 className="h-4 w-4" />
    </div>
  );
}
