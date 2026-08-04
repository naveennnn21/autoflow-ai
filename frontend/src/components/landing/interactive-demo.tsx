"use client";

import * as React from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Check, Sparkles } from "lucide-react";
import { Icon } from "@/components/shared/icons";
import { cn } from "@/lib/utils";
import { useTypingEffect } from "@/hooks/use-typing-effect";

type Phase = "prompt" | "planning" | "built" | "executing" | "completed";

const PROMPT = "When I receive an invoice in Gmail, save it to Drive and notify my finance team in Slack.";

const STAGES: { id: Phase; label: string }[] = [
  { id: "prompt", label: "Prompt" },
  { id: "planning", label: "Planning" },
  { id: "built", label: "Workflow generated" },
  { id: "executing", label: "Executing" },
  { id: "completed", label: "Completed" },
];

const NODES = [
  { id: "gmail", label: "Gmail", sub: "New invoice", icon: "mail", color: "text-[#EA4335]", phase: "trigger" },
  { id: "ai", label: "AI Extract", sub: "Parse + validate", icon: "brain", color: "text-primary", phase: "ai" },
  { id: "drive", label: "Google Drive", sub: "Save file", icon: "hard-drive", color: "text-[#4285F4]", phase: "action" },
  { id: "slack", label: "Slack", sub: "Notify finance", icon: "slack", color: "text-[#611f69]", phase: "action" },
];

const PHASE_TIMING: Record<Phase, number> = {
  prompt: 2400,
  planning: 2600,
  built: 2600,
  executing: 3200,
  completed: 2200,
};

export function InteractiveDemo() {
  const reduceMotion = useReducedMotion();
  const [phase, setPhase] = React.useState<Phase>("prompt");
  const [cycle, setCycle] = React.useState(0);

  // Typed prompt (re-types every cycle)
  const typed = useTypingEffect(PROMPT, { enabled: phase === "prompt", speed: 28 });

  // Advance through phases
  React.useEffect(() => {
    if (reduceMotion) return;
    const order: Phase[] = ["prompt", "planning", "built", "executing", "completed"];
    const idx = order.indexOf(phase);
    const t = window.setTimeout(() => {
      if (idx === order.length - 1) {
        setCycle((c) => c + 1);
        setPhase("prompt");
      } else {
        setPhase(order[idx + 1]);
      }
    }, PHASE_TIMING[phase]);
    return () => window.clearTimeout(t);
  }, [phase, reduceMotion]);

  // Which nodes are "built" (assembled into the graph)
  // During planning, nodes assemble one by one
  const [assembled, setAssembled] = React.useState(0);
  React.useEffect(() => {
    if (reduceMotion) return;
    if (phase !== "planning") {
      setAssembled(phase === "built" || phase === "executing" || phase === "completed" ? NODES.length : 0);
      return;
    }
    setAssembled(0);
    const timers = NODES.map((_, i) =>
      window.setTimeout(() => setAssembled(i + 1), 350 + i * 520),
    );
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [phase, cycle, reduceMotion]);

  // Execution: node lights up sequentially
  const executedNode = phase === "executing" ? "ai" : phase === "completed" ? "slack" : null;
  const [execIdx, setExecIdx] = React.useState(-1);
  React.useEffect(() => {
    if (reduceMotion) return;
    if (phase !== "executing") {
      setExecIdx(-1);
      return;
    }
    setExecIdx(0);
    const timers = NODES.map((_, i) => window.setTimeout(() => setExecIdx(i + 1), 900 + i * 650));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [phase, cycle, reduceMotion]);

  const phaseIdx = STAGES.findIndex((s) => s.id === phase);

  return (
    <div className="relative mx-auto max-w-4xl overflow-hidden rounded-2xl border border-border/70 bg-background/70 shadow-[0_48px_120px_-40px_rgba(0,0,0,0.8)] backdrop-blur-xl">
      {/* Window chrome */}
      <div className="flex items-center gap-3 border-b border-border/60 px-5 py-3.5">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#FB7185]/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#FBBF24]/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#4ADE80]/70" />
        </div>
        <p className="font-mono text-[11px] text-muted-foreground">autoflow.ai/copilot</p>
        <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-0.5 text-[10px] font-medium text-success">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-soft" />
          Live
        </span>
      </div>

      <div className="grid gap-0 md:grid-cols-[1fr_1.4fr]">
        {/* Left: prompt + phases */}
        <div className="flex flex-col border-b border-border/60 p-5 md:border-b-0 md:border-r">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <p className="text-xs font-medium text-muted-foreground">Describe an automation</p>
          </div>
          <div className="min-h-[92px] rounded-xl border border-border/70 bg-background/50 px-4 py-3 font-mono text-[13px] leading-relaxed text-foreground/90">
            {phase === "prompt" ? (
              <span>
                {typed.display}
                <span className="ml-px inline-block h-4 w-[2px] translate-y-[3px] animate-pulse bg-primary" />
              </span>
            ) : (
              <span className="text-foreground/60">{PROMPT}</span>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-1.5">
            {STAGES.map((s, i) => {
              const done = i < phaseIdx || phase === "completed";
              const active = i === phaseIdx;
              return (
                <div
                  key={s.id}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all duration-500",
                    done && "border-success/30 bg-success/10 text-success",
                    active && "border-primary/40 bg-primary/10 text-primary",
                    !done && !active && "border-border/70 text-muted-foreground/60",
                  )}
                >
                  {done ? (
                    <Check className="h-3 w-3" />
                  ) : active ? (
                    <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-soft" />
                  ) : null}
                  {s.label}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: workflow graph */}
        <div className="relative flex items-center justify-center p-6">
          <div aria-hidden className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,hsl(var(--primary)/0.06),transparent_65%)]" />
          <div className="relative w-full">
            {/* Node pipeline */}
            <div className="flex items-center justify-between gap-2">
              {NODES.map((node, i) => {
                const isBuilt = i < assembled || phase === "built" || phase === "executing" || phase === "completed";
                const isExecuted = executedNode !== null && i <= (phase === "completed" ? NODES.length - 1 : execIdx);
                const isExecuting = phase === "executing" && i === execIdx;
                return (
                  <React.Fragment key={node.id}>
                    {i > 0 && (
                      <div className="relative h-px flex-1 overflow-hidden bg-border/60">
                        {phase !== "prompt" && phase !== "planning" && (
                          <motion.div
                            key={`line-${i}`}
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: 1 }}
                            transition={{ duration: 0.5, delay: 0.2 + i * 0.15, ease: [0.22, 1, 0.36, 1] }}
                            className="absolute inset-0 origin-left bg-gradient-to-r from-primary/60 to-primary"
                          />
                        )}
                        {(isExecuted || phase === "completed") && (
                          <div
                            className="absolute inset-y-0 w-4 animate-[beam_1.1s_linear_infinite] bg-gradient-to-r from-transparent via-primary to-transparent"
                            style={{ animationDelay: `${i * 0.65}s` }}
                          />
                        )}
                      </div>
                    )}
                    <AnimatePresence>
                      {isBuilt && (
                        <motion.div
                          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.7, y: 14 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                          transition={{ type: "spring", stiffness: 300, damping: 22 }}
                          className={cn(
                            "relative flex w-[104px] shrink-0 flex-col items-center gap-1.5 rounded-xl border px-2 py-3 transition-colors duration-500 sm:w-[118px]",
                            isExecuted || phase === "completed"
                              ? "border-success/40 bg-success/8"
                              : isExecuting
                                ? "border-primary/60 bg-primary/10 shadow-[0_0_32px_-8px_hsl(var(--primary)/0.6)]"
                                : "border-border/80 bg-background/60",
                          )}
                        >
                          {isExecuted && (
                            <motion.span
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-success text-white shadow-[0_0_16px_hsl(var(--success)/0.8)]"
                            >
                              <Check className="h-3 w-3" />
                            </motion.span>
                          )}
                          <Icon name={node.icon} className={cn("h-5 w-5", node.color)} />
                          <div className="text-center">
                            <p className="text-[11px] font-semibold leading-tight">{node.label}</p>
                            <p className="text-[9px] text-muted-foreground">{node.sub}</p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </React.Fragment>
                );
              })}
            </div>

            {/* Status strip */}
            <div className="mt-5 flex h-9 items-center justify-between rounded-lg border border-border/60 bg-background/50 px-3.5">
              <AnimatePresence mode="wait">
                {phase === "completed" ? (
                  <motion.p
                    key="done"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-xs font-medium text-success"
                  >
                    <Check className="h-3.5 w-3.5" />
                    Invoice filed · finance notified · 3.1s
                  </motion.p>
                ) : phase === "executing" ? (
                  <motion.p
                    key="exec"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-xs font-medium text-primary"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-soft" />
                    Executing workflow
                  </motion.p>
                ) : phase === "built" ? (
                  <motion.p
                    key="built"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="text-xs font-medium text-muted-foreground"
                  >
                    Spec compiled · validated · ready to deploy
                  </motion.p>
                ) : phase === "planning" ? (
                  <motion.p
                    key="plan"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-xs font-medium text-primary"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-soft" />
                    {["Understanding request", "Finding connectors", "Building workflow", "Validating graph"][Math.min(assembled, 3)]}
                  </motion.p>
                ) : (
                  <motion.p
                    key="idle"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-xs text-muted-foreground/70"
                  >
                    Waiting for your description…
                  </motion.p>
                )}
              </AnimatePresence>
              <span className="font-mono text-[10px] text-muted-foreground/70">4 steps · 3 connectors</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
