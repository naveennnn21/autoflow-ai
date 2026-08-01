"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Rocket, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/shared/icons";
import type { WorkflowPreview } from "@/types";

const phaseLabels = ["Compiling workflow spec", "Validating graph", "Deploying"];

export function WorkflowPreviewCard({ preview }: { preview: WorkflowPreview }) {
  const [phase, setPhase] = React.useState<number | null>(null);
  const [done, setDone] = React.useState(false);

  const deploy = () => {
    setPhase(0);
    setDone(false);
    phaseLabels.forEach((_, i) => {
      setTimeout(() => setPhase(i), i * 700);
    });
    setTimeout(() => {
      setPhase(null);
      setDone(true);
    }, phaseLabels.length * 700 + 400);
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
                <Check className="h-3 w-3" /> Deployed
              </motion.span>
            ) : (
              <motion.span
                key="ready"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground"
              >
                Ready to deploy
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

        <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-border bg-background/40 px-3 py-2">
          <span className="text-xs text-muted-foreground">{preview.estimate}</span>
          <div className="flex gap-2">
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
            <Button size="sm" variant={done ? "secondary" : "default"} onClick={deploy}>
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
