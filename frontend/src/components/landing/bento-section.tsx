"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Sparkles, GitBranch, Boxes, Gauge, Shield, Rocket } from "lucide-react";
import { cn } from "@/lib/utils";

const cards = [
  { title: "AI Planning", desc: "Describe your workflow in plain language. The planner compiles it instantly.", icon: Sparkles, color: "from-primary/20 to-primary/5", accent: "text-primary" },
  { title: "130+ Actions", desc: "Pre-built actions for every connector — read, write, search, upload, batch.", icon: GitBranch, color: "from-info/20 to-info/5", accent: "text-info" },
  { title: "26 Connectors", desc: "Slack, Gmail, GitHub, Stripe, Notion and more. OAuth built-in.", icon: Boxes, color: "from-accent/20 to-accent/5", accent: "text-accent" },
  { title: "Live Execution", desc: "Millisecond-latency streaming graph execution. Watch nodes light up in real time.", icon: Gauge, color: "from-success/20 to-success/5", accent: "text-success" },
  { title: "Observability", desc: "Per-node latency, cost, success rates, and retry traces. Debug in seconds.", icon: Shield, color: "from-warning/20 to-warning/5", accent: "text-warning" },
  { title: "Encrypted Secrets", desc: "Credentials encrypted at rest. SOC 2 compliant. Tenant-isolated.", icon: Rocket, color: "from-destructive/20 to-destructive/5", accent: "text-destructive" },
];

export function BentoSection() {
  const rm = useReducedMotion();
  return (
    <section id="product" className="py-28 lg:py-36">
      <div className="container">
        <p className="eyebrow mb-4 text-center">Platform</p>
        <p className="text-section max-w-3xl mx-auto text-center balance">Everything you need to automate.</p>
        <div className="grid gap-4 mt-16 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((c, i) => (
            <motion.div key={c.title}
              initial={rm ? {opacity:1} : {opacity:0, y:20}}
              whileInView={{opacity:1, y:0}}
              viewport={{once: true}}
              transition={{delay: i*0.08, duration: 0.5, ease: [0.22,1,0.36,1]}}
              whileHover={rm ? {} : {y:-4}}
              className={cn("rounded-2xl border border-border/60 bg-card/60 p-6 backdrop-blur-sm transition-colors hover:border-border/90 group relative overflow-hidden", c.color)}
            >
              <div aria-hidden className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-0 blur-3xl transition-opacity group-hover:opacity-100" style={{background: "hsl(var(--primary) / 0.1)"}} />
              <c.icon className={cn("h-6 w-6 mb-4", c.accent)} />
              <p className="text-lg font-semibold tracking-tight mb-2">{c.title}</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{c.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
