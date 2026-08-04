"use client";

import { cn } from "@/lib/utils";

interface SectionGlowProps {
  className?: string;
  /** Opacity of the glow band */
  opacity?: number;
  color?: string;
}

export function SectionGlow({ className, opacity = 0.5, color = "hsl(var(--primary) / 0.1)" }: SectionGlowProps) {
  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-x-0 top-0 h-64", className)}
      style={{
        background: `radial-gradient(ellipse 55% 100% at 50% 0%, ${color}, transparent 70%)`,
        opacity,
      }}
    />
  );
}
