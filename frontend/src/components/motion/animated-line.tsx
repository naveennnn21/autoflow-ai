"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface AnimatedLineProps {
  /** SVG path `d` attribute */
  d: string;
  className?: string;
  color?: string;
  strokeWidth?: number;
  delay?: number;
  duration?: number;
  /** Animate dashes flowing along the drawn path */
  flowing?: boolean;
  viewBox?: string;
}

/**
 * Draws an SVG path progressively (pathLength 0 → 1) when in view.
 * Optionally overlays a flowing dash for direction.
 */
export function AnimatedLine({
  d,
  className,
  color = "hsl(var(--primary))",
  strokeWidth = 1.5,
  delay = 0,
  duration = 1.4,
  flowing = false,
  viewBox = "0 0 400 400",
}: AnimatedLineProps) {
  const reduceMotion = useReducedMotion();

  return (
    <svg aria-hidden viewBox={viewBox} fill="none" className={cn("pointer-events-none", className)}>
      <motion.path
        d={d}
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        initial={reduceMotion ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
        whileInView={reduceMotion ? undefined : { pathLength: 1, opacity: 1 }}
        viewport={{ once: true, margin: "-15% 0px" }}
        transition={{ duration, delay, ease: [0.22, 1, 0.36, 1] }}
      />
      {flowing && !reduceMotion && (
        <motion.path
          d={d}
          stroke={color}
          strokeWidth={strokeWidth + 1.5}
          strokeLinecap="round"
          strokeDasharray="2 22"
          initial={{ pathLength: 0, opacity: 0 }}
          whileInView={{ pathLength: 1, opacity: 0.9 }}
          viewport={{ once: true, margin: "-15% 0px" }}
          transition={{ duration, delay: delay + duration * 0.6, ease: "linear" }}
          className="animate-dash-flow"
          style={{ filter: "blur(0.5px)" }}
        />
      )}
    </svg>
  );
}
