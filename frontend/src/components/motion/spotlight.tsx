"use client";

import * as React from "react";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SpotlightProps {
  children?: React.ReactNode;
  className?: string;
  /** Base color of the spotlight glow */
  color?: string;
  /** Inner element className */
  innerClassName?: string;
}

/**
 * Card with a soft spotlight that follows the cursor. Pure CSS variables —
 * no React re-renders, no layout thrash.
 */
export function Spotlight({ children, className, color = "hsl(var(--primary) / 0.14)", innerClassName }: SpotlightProps) {
  const reduceMotion = useReducedMotion();
  const ref = React.useRef<HTMLDivElement>(null);

  const onMove = React.useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (reduceMotion) return;
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      el.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
      el.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
    },
    [reduceMotion],
  );

  return (
    <div ref={ref} onMouseMove={onMove} className={cn("group/spot relative overflow-hidden", className)}>
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 z-0 opacity-0 transition-opacity duration-500 group-hover/spot:opacity-100",
          innerClassName,
        )}
        style={{
          background: `radial-gradient(420px circle at var(--spot-x, 50%) var(--spot-y, 50%), ${color}, transparent 65%)`,
        }}
      />
      {children}
    </div>
  );
}
