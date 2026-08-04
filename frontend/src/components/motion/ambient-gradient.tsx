"use client";

import { cn } from "@/lib/utils";

interface AmbientGradientProps {
  className?: string;
  /** Color blobs — CSS color strings */
  colors?: string[];
}

/**
 * Slow-moving ambient color field. CSS-only animation (transform driven) —
 * GPU friendly, ideal as a page-level backdrop.
 */
export function AmbientGradient({
  className,
  colors = ["hsl(var(--primary) / 0.16)", "hsl(var(--info) / 0.12)", "hsl(var(--accent) / 0.14)"],
}: AmbientGradientProps) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      {colors.map((c, i) => (
        <div
          key={i}
          className="absolute animate-drift rounded-full blur-[110px] will-change-transform"
          style={{
            background: c,
            width: `${42 + i * 6}%`,
            height: `${42 + i * 6}%`,
            left: `${[8, 55, 30][i % 3]}%`,
            top: `${[5, 35, 60][i % 3]}%`,
            animationDelay: `${i * 4}s`,
            animationDuration: `${20 + i * 5}s`,
          }}
        />
      ))}
    </div>
  );
}
