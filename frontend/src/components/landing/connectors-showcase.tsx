"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Icon } from "@/components/shared/icons";
import { cn } from "@/lib/utils";

const CONNECTOR_LOGOS = [
  { name: "Gmail", icon: "mail", color: "text-[#EA4335]" },
  { name: "Slack", icon: "slack", color: "text-[#611f69]" },
  { name: "GitHub", icon: "github", color: "text-[#24292F]" },
  { name: "Notion", icon: "notion", color: "text-[#111]" },
  { name: "Stripe", icon: "stripe", color: "text-[#635BFF]" },
  { name: "Shopify", icon: "shopping-bag", color: "text-[#96BF48]" },
  { name: "Discord", icon: "message-square", color: "text-[#5865F2]" },
];

export function ConnectorsShowcase() {
  const rm = useReducedMotion();
  return (
    <section id="integrations" className="py-28 lg:py-40 relative overflow-hidden">
      <div className="container text-center">
        <p className="eyebrow mb-4">Integrations</p>
        <h2 className="text-section max-w-3xl mx-auto balance">Everything connects.</h2>
        <p className="mt-4 text-body-lg text-muted-foreground max-w-lg mx-auto">
          200+ connectors. One OAuth flow. Every integration ships with automatic token refresh and rate-limit handling.
        </p>
        <div className="flex flex-wrap justify-center gap-3 mt-16">
          {CONNECTOR_LOGOS.map((c, i) => (
            <motion.div key={c.name}
              initial={rm ? {opacity:1} : {opacity:0, scale:0.8}}
              whileInView={{opacity:1, scale:1}}
              viewport={{once: true}}
              transition={{delay: i*0.06, duration: 0.5, ease: [0.22,1,0.36,1]}}
              whileHover={rm ? {} : {y:-6}}
              className="flex items-center gap-2.5 rounded-2xl border border-border/60 bg-card/70 px-4 py-3 backdrop-blur-sm hover:border-border/90">
              <Icon name={c.icon} className={cn("h-5 w-5", c.color)} />
              <span className="text-sm font-medium">{c.name}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
