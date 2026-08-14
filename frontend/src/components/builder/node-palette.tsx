"use client";

import { motion } from "framer-motion";
import {
  Braces,
  GitBranch,
  Play,
  PlugZap,
  Plus,
  Timer,
  Zap,
} from "lucide-react";
import { Icon } from "@/components/shared/icons";
import { cn } from "@/lib/utils";
import type { NodeKind } from "@/types";

interface PaletteItem {
  kind: NodeKind;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const ITEMS: PaletteItem[] = [
  {
    kind: "trigger",
    label: "Trigger",
    description: "Starts the workflow",
    icon: <Play className="h-4 w-4" />,
  },
  {
    kind: "action",
    label: "Action",
    description: "Run a connector action",
    icon: <Zap className="h-4 w-4" />,
  },
  {
    kind: "condition",
    label: "Condition",
    description: "Branch on a rule",
    icon: <GitBranch className="h-4 w-4" />,
  },
  {
    kind: "ai",
    label: "AI step",
    description: "LLM prompt / completion",
    icon: <Braces className="h-4 w-4" />,
  },
  {
    kind: "delay",
    label: "Wait",
    description: "Pause between steps",
    icon: <Timer className="h-4 w-4" />,
  },
  {
    kind: "webhook",
    label: "Webhook",
    description: "Inbound webhook",
    icon: <PlugZap className="h-4 w-4" />,
  },
];

export function NodePalette({
  onAdd,
  disabled,
}: {
  onAdd: (kind: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex w-44 shrink-0 flex-col gap-1.5 overflow-y-auto rounded-xl border border-border bg-card/60 p-2 no-scrollbar">
      <p className="px-1 pb-1 pt-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Add node
      </p>
      {ITEMS.map((item) => (
        <motion.button
          key={item.kind}
          whileHover={{ x: 2 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onAdd(item.kind)}
          disabled={disabled}
          className={cn(
            "group flex items-center gap-2.5 rounded-lg border border-border/60 bg-card px-2.5 py-2 text-left transition-colors",
            "hover:border-primary/40 hover:bg-primary/5 disabled:opacity-50",
          )}
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground transition-colors group-hover:bg-primary/15 group-hover:text-primary">
            {item.icon}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-xs font-medium">{item.label}</span>
            <span className="block truncate text-[10px] text-muted-foreground">
              {item.description}
            </span>
          </span>
          <Plus className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground/50 opacity-0 transition-opacity group-hover:opacity-100" />
        </motion.button>
      ))}
      <div className="mt-1 border-t border-border/50 px-1 pt-2">
        <p className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <Icon name="zap" className="h-3 w-3" />
          Drag handles to reconnect
        </p>
      </div>
    </div>
  );
}
