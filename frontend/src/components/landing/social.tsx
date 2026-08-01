"use client";

import * as React from "react";
import { Check, Quote, Minus, Plus, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FadeIn, StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { testimonials, pricingTiers, faqItems } from "@/lib/mock-content";
import { motion, AnimatePresence } from "framer-motion";

export function Testimonials() {
  return (
    <section className="relative py-24">
      <div className="container">
        <FadeIn className="mx-auto mb-12 max-w-2xl text-center">
          <Badge variant="gradient" className="mb-4">Loved by teams</Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">Trusted by operators everywhere</h2>
        </FadeIn>
        <StaggerGroup className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {testimonials.map((t) => (
            <StaggerItem key={t.name}>
              <Card className="card-hover h-full">
                <CardContent className="flex h-full flex-col p-6">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex gap-0.5 text-warning">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} className="h-3.5 w-3.5 fill-current" />
                      ))}
                    </div>
                    <Quote className="h-5 w-5 text-muted-foreground/40" />
                  </div>
                  <p className="flex-1 text-sm leading-relaxed">“{t.quote}”</p>
                  <div className="mt-5 flex items-center gap-3">
                    <div className={cn("flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br text-xs font-semibold text-white", t.avatarColor)}>
                      {t.name.split(" ").map((p) => p[0]).join("")}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{t.name}</p>
                      <p className="text-xs text-muted-foreground">{t.role} · {t.company}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </div>
    </section>
  );
}

export function Pricing() {
  return (
    <section id="pricing" className="relative py-24">
      <div className="container">
        <FadeIn className="mx-auto mb-12 max-w-2xl text-center">
          <Badge variant="gradient" className="mb-4">Pricing</Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">Simple pricing that scales</h2>
          <p className="mt-3 text-muted-foreground">Start free. Upgrade when your automations take off.</p>
        </FadeIn>
        <StaggerGroup className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-3">
          {pricingTiers.map((tier) => (
            <StaggerItem key={tier.name} className={cn(tier.highlight && "lg:-mt-4 lg:-mb-4")}>
              <Card className={cn("card-hover relative h-full", tier.highlight && "border-primary/50 shadow-glow")}>
                {tier.highlight && (
                  <Badge variant="gradient" className="absolute -top-3 left-1/2 -translate-x-1/2">Most popular</Badge>
                )}
                <CardContent className="flex h-full flex-col p-6">
                  <h3 className="font-semibold">{tier.name}</h3>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span className="text-4xl font-bold tracking-tight">${tier.price}</span>
                    <span className="text-sm text-muted-foreground">{tier.cadence}</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{tier.description}</p>
                  <ul className="mt-5 flex-1 space-y-2.5">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 shrink-0 text-success" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button variant={tier.highlight ? "gradient" : "outline"} className="mt-6 w-full" asChild>
                    <a href="/register">{tier.cta}</a>
                  </Button>
                </CardContent>
              </Card>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </div>
    </section>
  );
}

export function Faq() {
  const [open, setOpen] = React.useState<number | null>(0);
  return (
    <section id="faq" className="relative py-24">
      <div className="container max-w-3xl">
        <FadeIn className="mx-auto mb-12 max-w-2xl text-center">
          <Badge variant="gradient" className="mb-4">FAQ</Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">Frequently asked questions</h2>
        </FadeIn>
        <div className="space-y-3">
          {faqItems.map((item, i) => (
            <FadeIn key={item.question} delay={i * 0.05}>
              <div className="overflow-hidden rounded-xl border border-border bg-card">
                <button
                  onClick={() => setOpen(open === i ? null : i)}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium"
                >
                  {item.question}
                  {open === i ? <Minus className="h-4 w-4 shrink-0 text-primary" /> : <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />}
                </button>
                <AnimatePresence initial={false}>
                  {open === i && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                    >
                      <p className="px-5 pb-4 text-sm leading-relaxed text-muted-foreground">{item.answer}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
