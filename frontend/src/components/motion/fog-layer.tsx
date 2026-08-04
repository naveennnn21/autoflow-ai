"use client";

import { cn } from "@/lib/utils";

interface FogLayerProps {
  className?: string;
  /** Overall density of the fog masses */
  intensity?: "subtle" | "medium";
}

/**
 * Moving atmospheric fog.
 *
 * Three large blurred gradient masses drift on transform-only loops
 * (translate3d + scale) — GPU accelerated, zero layout/paint cost per frame.
 * Pure theme tokens, so it adapts to dark and light surfaces automatically.
 */
export function FogLayer({ className, intensity = "subtle" }: FogLayerProps) {
  const density = intensity === "subtle" ? "opacity-70" : "opacity-100";

  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className={cn("absolute inset-[-30%]", density)}>
        <div className="absolute left-[6%] top-[10%] h-[55%] w-[45%] animate-fog rounded-full bg-[radial-gradient(ellipse_at_center,hsl(var(--primary)/0.11),transparent_65%)] blur-[90px] will-change-transform" />
        <div className="absolute right-[4%] top-[28%] h-[60%] w-[50%] animate-fog-reverse rounded-full bg-[radial-gradient(ellipse_at_center,hsl(var(--info)/0.09),transparent_65%)] blur-[100px] will-change-transform [animation-delay:-12s]" />
        <div className="absolute bottom-[4%] left-[28%] h-[50%] w-[55%] animate-fog rounded-full bg-[radial-gradient(ellipse_at_center,hsl(var(--accent)/0.08),transparent_65%)] blur-[110px] will-change-transform [animation-delay:-24s]" />
      </div>
    </div>
  );
}
