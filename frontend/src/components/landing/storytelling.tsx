"use client";

import * as React from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { Check } from "lucide-react";
import { Icon } from "@/components/shared/icons";
import { WordReveal } from "@/components/motion/word-reveal";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    num: "01",
    title: "Describe it.",
    body: "One sentence is enough. No fields to map, no dropdowns to hunt through — you say what you want to happen, in your own words.",
  },
  {
    num: "02",
    title: "AI understands it.",
    body: "The planner parses intent, extracts entities and actions, and resolves ambiguities against every connector's real schema.",
  },
  {
    num: "03",
    title: "AutoFlow builds it.",
    body: "A validated workflow spec is compiled: triggers wired, dependencies ordered, error handling and retries inserted automatically.",
  },
  {
    num: "04",
    title: "Connect everything.",
    body: "One OAuth flow links your tools. Tokens refresh themselves. Rate limits and backoff are managed per connector, silently.",
  },
  {
    num: "05",
    title: "Run automatically.",
    body: "Every trigger fires your workflow in milliseconds. Node-by-node execution streams through the graph with full observability.",
  },
  {
    num: "06",
    title: "Observe everything.",
    body: "Per-node latency, cost, and success rates — live. When something fails, you see exactly where, why, and how it recovered.",
  },
] as const;

function JourneyVisual({ step }: { step: number }) {
  const reduceMotion = useReducedMotion();
  const nodes = [
    { icon: "mail", label: "Gmail", x: "6%", y: "20%", color: "text-[#EA4335]" },
    { icon: "brain", label: "AI", x: "40%", y: "4%", color: "text-primary" },
    { icon: "hard-drive", label: "Drive", x: "40%", y: "62%", color: "text-[#4285F4]" },
    { icon: "slack", label: "Slack", x: "74%", y: "30%", color: "text-[#611f69]" },
  ];

  const builtAt = [0, 1, 2, 4, 4, 4];
  const built = builtAt[step] ?? 4;
  const now = Math.floor(Date.now() / 700) % 4;

  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-b from-background-2 to-background sm:aspect-square lg:aspect-[4/3]">
      <div aria-hidden className="absolute inset-0 bg-grid opacity-30 [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)]" />
      {step >= 2 && !reduceMotion && (
        <svg aria-hidden className="absolute inset-0 h-full w-full" viewBox="0 0 400 400" fill="none">
          {[
            "M140 130 C 180 60, 230 50, 275 95",
            "M140 175 C 180 190, 220 205, 275 230",
            "M300 170 C 320 185, 325 200, 315 215",
          ].map((d, i) => (
            <motion.path
              key={i}
              d={d}
              stroke="hsl(var(--primary) / 0.45)"
              strokeWidth="1.5"
              strokeDasharray={step >= 4 ? "3 8" : undefined}
              className={step >= 4 ? "animate-dash-flow" : undefined}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.8, delay: 0.2 * i, ease: [0.22, 1, 0.36, 1] }}
            />
          ))}
        </svg>
      )}

      {/* Prompt bubble (step 0-1) */}
      <div className="absolute inset-x-8 top-8">
        <motion.div
          animate={{ opacity: step <= 1 ? 1 : 0, y: step <= 1 ? 0 : -12 }}
          transition={{ duration: 0.4 }}
          className="mx-auto max-w-sm rounded-xl border border-border/70 bg-card/90 px-4 py-3 font-mono text-[11px] leading-relaxed shadow-soft backdrop-blur-xl"
        >
          <span className="text-primary">&ldquo;</span>Route urgent support emails to Slack and log them to Airtable<span className="text-primary">&rdquo;</span>
        </motion.div>
      </div>

      {/* Understanding chips (step 1-2) */}
      <div className="absolute inset-x-6 top-36 flex flex-wrap justify-center gap-2">
        {["Trigger: Email", "Intent: Route", "Action: Notify", "Target: Airtable"].map((c, i) => (
          <motion.span
            key={c}
            animate={{ opacity: step >= 1 ? 1 : 0, y: step >= 1 ? 0 : 8 }}
            transition={{ duration: 0.3, delay: i * 0.12 }}
            className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] font-medium text-primary"
          >
            {c}
          </motion.span>
        ))}
      </div>

      {/* Nodes */}
      {nodes.map((n, i) => {
        const isBuilt = i < built;
        const running = step === 4 && i === now;
        const done = step === 5 || (step === 4 && i < now);
        return (
          <motion.div
            key={n.icon}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: n.x }}
            initial={false}
            animate={{
              opacity: isBuilt ? 1 : 0,
              scale: isBuilt ? 1 : 0.6,
              top: isBuilt ? n.y : "50%",
            }}
            transition={{ type: "spring", stiffness: 260, damping: 24, delay: step === 2 ? i * 0.18 : 0 }}
          >
            <div
              className={cn(
                "flex flex-col items-center gap-1 rounded-xl border px-3.5 py-2.5 backdrop-blur-xl transition-colors duration-500",
                done
                  ? "border-success/40 bg-success/10"
                  : running
                    ? "border-primary/60 bg-primary/10 shadow-[0_0_28px_-6px_hsl(var(--primary)/0.7)]"
                    : "border-border/70 bg-card/90",
              )}
            >
              <Icon name={n.icon} className={cn("h-5 w-5", n.color)} />
              <span className="text-[10px] font-medium">{n.label}</span>
              {(done || running) && <Check className="h-3 w-3 text-success" />}
            </div>
          </motion.div>
        );
      })}

      {/* Completion summary (step 5) */}
      <motion.div
        animate={{ opacity: step === 5 ? 1 : 0, y: step === 5 ? 0 : 10 }}
        transition={{ duration: 0.4 }}
        className="absolute inset-x-8 bottom-6 flex items-center justify-between rounded-xl border border-success/30 bg-success/8 px-4 py-2.5 backdrop-blur-xl"
      >
        <span className="text-xs font-medium text-success">Automation running · 99.2% success</span>
        <span className="font-mono text-[10px] text-muted-foreground">1.8s avg</span>
      </motion.div>
    </div>
  );
}

export function Storytelling() {
  const reduceMotion = useReducedMotion();
  const ref = React.useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const step = useTransform(scrollYProgress, [0, 0.96], [0, STEPS.length - 1]);
  const [active, setActive] = React.useState(0);

  React.useEffect(() => {
    return step.on("change", (v) => setActive(Math.round(v)));
  }, [step]);

  return (
    <section id="solutions" className="relative">
      <div ref={ref} className="relative" style={{ height: reduceMotion ? "auto" : "420vh" }}>
        <div className={cn("sticky top-0 flex min-h-screen flex-col justify-center overflow-hidden py-24", reduceMotion && "relative")}>
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(ellipse_60%_100%_at_50%_0%,hsl(var(--accent)/0.08),transparent_70%)]" />
          <div className="container grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
            {/* Text column */}
            <div className={cn("order-2 lg:order-1", reduceMotion && "space-y-16")}>
              {reduceMotion ? (
                STEPS.map((s) => (
                  <div key={s.num} className="border-t border-border/60 pt-6">
                    <p className="eyebrow mb-3">Step {s.num}</p>
                    <h3 className="text-display">{s.title}</h3>
                    <p className="mt-3 max-w-md text-body-lg text-muted-foreground">{s.body}</p>
                  </div>
                ))
              ) : (
                <div className="relative h-[420px]">
                  {STEPS.map((s, i) => (
                    <motion.div
                      key={s.num}
                      animate={{ opacity: i === active ? 1 : 0, y: i === active ? 0 : 20 }}
                      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                      className="absolute inset-0 flex flex-col justify-center"
                      aria-hidden={i !== active}
                    >
                      <p className="eyebrow mb-4 flex items-center gap-3">
                        <span>Step {s.num}</span>
                        <span className="h-px w-10 bg-border" />
                        <span className="font-mono normal-case tracking-normal text-muted-foreground/60">
                          {i + 1} / {STEPS.length}
                        </span>
                      </p>
                      <h3 className="text-display max-w-md">
                        <WordReveal text={s.title} />
                      </h3>
                      <p className="mt-4 max-w-md text-body-lg text-muted-foreground">{s.body}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* Visual column */}
            <div className={cn("order-1 lg:order-2", reduceMotion && "lg:sticky lg:top-24")}>
              <JourneyVisual step={active} />
            </div>
          </div>

          {/* Progress rail */}
          {!reduceMotion && (
            <div className="container mt-14 hidden lg:block">
              <div className="flex items-center gap-2">
                {STEPS.map((s, i) => (
                  <div key={s.num} className="flex flex-1 flex-col gap-2">
                    <div className="h-1 overflow-hidden rounded-full bg-border/50">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-info"
                        initial={false}
                        animate={{ width: i <= active ? "100%" : "0%" }}
                        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                      />
                    </div>
                    <span className={cn("text-[10px] font-medium uppercase tracking-wider transition-colors", i <= active ? "text-foreground" : "text-muted-foreground/50")}>
                      {s.title.replace(".", "")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
