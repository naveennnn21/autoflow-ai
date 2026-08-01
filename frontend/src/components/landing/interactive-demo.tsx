"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Check } from "lucide-react";
import { GlowBorder } from "@/components/motion/glow-border";
import { Icon } from "@/components/shared/icons";
import { cn } from "@/lib/utils";

const steps = [
  { label: "New email detected", connector: "gmail", status: "success" },
  { label: "Classifying intent", connector: "ai", status: "running" },
  { label: "Routing to #support", connector: "slack", status: "waiting" },
  { label: "Logging to Airtable", connector: "table", status: "waiting" },
];

export function InteractiveDemo() {
  const [phase, setPhase] = React.useState(0);

  React.useEffect(() => {
    const t = setInterval(() => setPhase((p) => (p >= steps.length ? 0 : p + 1)), 1100);
    return () => clearInterval(t);
  }, []);

  return (
    <GlowBorder className="text-left">
      <div className="rounded-xl bg-card/80 p-5 backdrop-blur-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-rose-500/80" />
            <span className="flex h-2 w-2 rounded-full bg-warning/80" />
            <span className="flex h-2 w-2 rounded-full bg-success/80" />
          </div>
          <div className="flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-[11px] text-muted-foreground">
            <Play className="h-3 w-3" />
            Live simulation
          </div>
        </div>

        <div className="mb-3 rounded-lg border border-border bg-background/60 px-3 py-2 font-mono text-xs text-muted-foreground">
          “When a new email arrives, classify it and alert the support team in Slack”
        </div>

        <div className="space-y-2">
          {steps.map((step, i) => {
            const done = i < phase;
            const running = i === phase;
            return (
              <div
                key={step.label}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-all duration-500",
                  done && "border-success/30 bg-success/5",
                  running && "border-primary/40 bg-primary/5 shadow-glow",
                  !done && !running && "border-border bg-muted/20 opacity-60",
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
                    done && "bg-success/15 text-success",
                    running && "bg-primary/15 text-primary",
                    !done && !running && "bg-muted text-muted-foreground",
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : <Icon name={step.connector} className="h-3.5 w-3.5" />}
                </span>
                <span className="font-medium">{step.label}</span>
                {running && (
                  <span className="ml-auto flex gap-1">
                    {[0, 1, 2].map((d) => (
                      <span key={d} className="h-1 w-1 rounded-full bg-primary animate-bounce-dot" style={{ animationDelay: `${d * 0.15}s` }} />
                    ))}
                  </span>
                )}
                {done && <span className="ml-auto text-[10px] font-medium text-success">✓ done</span>}
              </div>
            );
          })}
        </div>

        <AnimatePresence>
          {phase >= steps.length && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-3 flex items-center justify-between rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-xs text-success"
            >
              <span className="font-medium">Workflow compiled & deployed</span>
              <span className="font-mono">4.2s · 98.6% success</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </GlowBorder>
  );
}
