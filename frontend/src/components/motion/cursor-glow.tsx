"use client";

import * as React from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

export function CursorGlow() {
  const mx = useMotionValue(-400);
  const my = useMotionValue(-400);
  const x = useSpring(mx, { stiffness: 90, damping: 20, mass: 0.5 });
  const y = useSpring(my, { stiffness: 90, damping: 20, mass: 0.5 });

  React.useEffect(() => {
    function onMove(e: MouseEvent) {
      mx.set(e.clientX - 200);
      my.set(e.clientY - 200);
    }
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [mx, my]);

  return (
    <motion.div
      aria-hidden
      style={{ x, y }}
      className="pointer-events-none fixed left-0 top-0 z-[5] hidden size-[400px] rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--primary)/0.07),transparent_60%)] md:block"
    />
  );
}
