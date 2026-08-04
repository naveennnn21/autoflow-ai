"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AmbientGradient } from "@/components/motion/ambient-gradient";
import { DotGrid } from "@/components/motion/dot-grid";
import { Magnetic } from "@/components/motion/magnetic";
import { WordReveal } from "@/components/motion/word-reveal";
import { InteractiveDemo } from "./interactive-demo";

export function Hero() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="relative flex min-h-[100svh] flex-col overflow-hidden">
      <AmbientGradient colors={["hsl(var(--primary) / 0.14)", "hsl(var(--info) / 0.1)", "hsl(var(--accent) / 0.12)"]} />
      <DotGrid className="opacity-40 [mask-image:radial-gradient(ellipse_70%_50%_at_50%_35%,black,transparent)]" />
      <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-background to-transparent" />

      <div className="container relative flex flex-1 flex-col justify-center pb-16 pt-36 sm:pt-40">
        <div className="max-w-5xl">
          <motion.div
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="mb-8 flex items-center gap-3"
          >
            <span className="inline-flex h-2 w-2 rounded-full bg-success shadow-[0_0_12px_hsl(var(--success))] animate-pulse-soft" />
            <p className="text-[13px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              The AI automation platform
            </p>
          </motion.div>

          <h1 className="text-hero text-shadow-hero">
            <WordReveal text="Automate anything." as="span" className="block" />
            <WordReveal text="Just describe it." as="span" delay={0.35} className="block gradient-text-soft" />
          </h1>

          <motion.p
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.9, ease: [0.22, 1, 0.36, 1] }}
            className="mt-8 max-w-xl text-body-lg text-muted-foreground"
          >
            Describe what you want. AutoFlow plans it, builds it, and runs it — across 200+ tools, with no code.
          </motion.p>

          <motion.div
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 1.05, ease: [0.22, 1, 0.36, 1] }}
            className="mt-10 flex flex-col items-start gap-3 sm:flex-row sm:items-center"
          >
            <Magnetic>
              <Button size="lg" asChild className="group h-12 rounded-full px-8 text-base shadow-[0_8px_32px_-8px_hsl(var(--primary)/0.6)]">
                <Link href="/register">
                  Start building
                  <ArrowRight className="transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
              </Button>
            </Magnetic>
            <Magnetic strength={0.25}>
              <Button size="lg" variant="ghost" asChild className="h-12 rounded-full px-6 text-base">
                <Link href="#product">See how it works</Link>
              </Button>
            </Magnetic>
          </motion.div>

          <motion.p
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, delay: 1.2 }}
            className="mt-6 text-xs text-muted-foreground/80"
          >
            Free forever plan · No credit card required · SOC 2 Type II
          </motion.p>
        </div>
      </div>

      <div className="container relative pb-10">
        <motion.div
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 48 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 1.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <InteractiveDemo />
        </motion.div>
      </div>
    </section>
  );
}
