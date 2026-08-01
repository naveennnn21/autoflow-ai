"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuroraBackground } from "@/components/motion/aurora-background";
import { Particles } from "@/components/motion/particles";
import { LightBeams } from "@/components/motion/light-beams";
import { GradientOrb } from "@/components/motion/gradient-orb";
import { Magnetic } from "@/components/motion/magnetic";
import { Badge } from "@/components/ui/badge";
import { InteractiveDemo } from "./interactive-demo";

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] as const },
});

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40">
      <AuroraBackground />
      <Particles />
      <LightBeams />
      <GradientOrb color="primary" className="left-[8%] top-[12%] size-72" />
      <GradientOrb color="secondary" className="right-[6%] top-[30%] size-80" />
      <GradientOrb color="accent" className="bottom-[8%] left-[38%] size-64" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,transparent_0%,hsl(var(--background))_72%)]" />

      <div className="container relative text-center">
        <motion.div {...fadeUp(0)} className="mb-6 flex justify-center">
          <Badge variant="gradient" className="gap-2 rounded-full px-3 py-1 text-xs">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Meet the AI automation platform
          </Badge>
        </motion.div>

        <motion.h1
          {...fadeUp(0.1)}
          className="mx-auto max-w-4xl text-balance text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl"
        >
          Automations that
          <br />
          <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient-x">
            build themselves
          </span>
        </motion.h1>

        <motion.p
          {...fadeUp(0.2)}
          className="mx-auto mt-6 max-w-2xl text-balance text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
          Describe what you want in plain English. AutoFlow&apos;s AI planner designs the workflow,
          compiles a validated spec, and connects 200+ tools — no code, no prompts, no waiting.
        </motion.p>

        <motion.div
          {...fadeUp(0.3)}
          className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Magnetic>
            <Button variant="gradient" size="lg" asChild className="group">
              <Link href="/register">
                Start building free
                <ArrowRight className="transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </Magnetic>
          <Magnetic strength={0.25}>
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">
                <Zap className="text-warning" />
                View live demo
              </Link>
            </Button>
          </Magnetic>
        </motion.div>

        <motion.p {...fadeUp(0.4)} className="mt-5 text-xs text-muted-foreground">
          Free forever plan · No credit card required · SOC 2 Type II
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="mx-auto mt-14 max-w-4xl"
        >
          <InteractiveDemo />
        </motion.div>
      </div>
    </section>
  );
}
