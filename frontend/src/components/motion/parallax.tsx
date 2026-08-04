"use client";

import * as React from "react";
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

interface ParallaxProps {
  children: React.ReactNode;
  className?: string;
  /** How far the element travels, in px (positive = moves up slower, negative = down) */
  offset?: number;
}

/**
 * Subtle scroll parallax. Transforms `y` based on the element's position
 * relative to the viewport. Pure transform-based (60fps friendly).
 */
export function Parallax({ children, className, offset = 80 }: ParallaxProps) {
  const reduceMotion = useReducedMotion();
  const ref = React.useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useSpring(useTransform(scrollYProgress, [0, 1], [offset, -offset]), {
    stiffness: 120,
    damping: 24,
    restDelta: 0.001,
  });

  if (reduceMotion) {
    return <div ref={ref} className={className}>{children}</div>;
  }

  return (
    <motion.div ref={ref} style={{ y }} className={cn("will-change-transform", className)}>
      {children}
    </motion.div>
  );
}
