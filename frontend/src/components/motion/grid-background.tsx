"use client";

import { cn } from "@/lib/utils";

interface GridBackgroundProps {
  className?: string;
  /** Fade the grid toward the edges of the container */
  fade?: boolean;
  /** Grid cell size in px */
  size?: number;
}

export function GridBackground({ className, fade = false, size = 56 }: GridBackgroundProps) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0", className)}>
      <div
        className={cn("absolute inset-0 bg-grid", fade && "bg-grid-fade")}
        style={!fade ? { backgroundSize: `${size}px ${size}px` } : undefined}
      />
      {fade && (
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_0%,transparent_30%,hsl(var(--background))_100%)]" />
      )}
    </div>
  );
}
