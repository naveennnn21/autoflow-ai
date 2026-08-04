"use client";

import { cn } from "@/lib/utils";

interface NoiseOverlayProps {
  className?: string;
  strong?: boolean;
}

/**
 * Subtle film-grain noise. Static (no animation) for zero runtime cost.
 */
export function NoiseOverlay({ className, strong = false }: NoiseOverlayProps) {
  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-0", strong ? "bg-noise-strong" : "bg-noise", className)}
    />
  );
}
