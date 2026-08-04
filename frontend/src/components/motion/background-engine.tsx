"use client";

import * as React from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { cn } from "@/lib/utils";
import { AmbientGradient } from "./ambient-gradient";
import { FogLayer } from "./fog-layer";
import { LightBeams } from "./light-beams";
import { Particles } from "./particles";
import { NoiseOverlay } from "./noise-overlay";
import { GradientOrb } from "./gradient-orb";

interface BackgroundEngineProps {
  className?: string;
  /** atmospheric = full scene · minimal = quiet backdrop */
  variant?: "atmospheric" | "minimal";
  mesh?: boolean;
  fog?: boolean;
  beams?: boolean;
  particles?: boolean;
  noise?: boolean;
  orbs?: boolean;
  spotlight?: boolean;
  depth?: boolean;
  particleCount?: number;
}

const ORBS: { color: "primary" | "secondary" | "accent"; className: string }[] = [
  { color: "primary", className: "left-[10%] top-[16%] h-72 w-72" },
  { color: "accent", className: "right-[8%] top-[30%] h-80 w-80" },
  { color: "secondary", className: "bottom-[12%] left-[38%] h-64 w-64" },
];

/**
 * Reusable atmospheric background engine.
 *
 * Composes seven GPU-friendly depth layers — animated mesh, moving fog,
 * light rays, glow blobs, mouse spotlight, floating particles and film grain.
 * Every layer is pointer-transparent, token-driven and disabled under
 * prefers-reduced-motion. Pass positioning yourself (e.g. "fixed inset-0 -z-10"
 * for a page backdrop or "absolute inset-0" inside a section).
 */
export function BackgroundEngine({
  className,
  variant = "atmospheric",
  mesh,
  fog,
  beams,
  particles,
  noise,
  orbs,
  spotlight,
  depth,
  particleCount,
}: BackgroundEngineProps) {
  const reduceMotion = useReducedMotion();

  const layers = {
    mesh: mesh ?? true,
    fog: fog ?? true,
    beams: beams ?? variant === "atmospheric",
    particles: particles ?? variant === "atmospheric",
    noise: noise ?? true,
    orbs: orbs ?? variant === "atmospheric",
    spotlight: spotlight ?? true,
    depth: depth ?? variant === "atmospheric",
  };

  return (
    <div aria-hidden className={cn("pointer-events-none overflow-hidden", className)}>
      {/* Depth 1 — ambient color field */}
      {layers.mesh && <AmbientGradient className="absolute inset-0" />}

      {/* Depth 2 — moving fog */}
      {layers.fog && <FogLayer className="absolute inset-0" />}

      {/* Depth 3 — light rays (parallax only when depth is enabled) */}
      {layers.beams && (
        <DepthLayer factor={layers.depth ? 0.6 : 0} reduceMotion={reduceMotion} className="absolute inset-0">
          <LightBeams className="absolute inset-0" />
        </DepthLayer>
      )}

      {/* Depth 4 — glow blobs (parallax only when depth is enabled) */}
      {layers.orbs && (
        <DepthLayer factor={layers.depth ? 1.4 : 0} reduceMotion={reduceMotion} className="absolute inset-0">
          {ORBS.map((o) => (
            <GradientOrb key={o.color} color={o.color} className={o.className} />
          ))}
        </DepthLayer>
      )}

      {/* Depth 5 — mouse spotlight */}
      {layers.spotlight && <MouseSpotlight reduceMotion={reduceMotion} />}

      {/* Depth 6 — floating particles */}
      {layers.particles && <Particles className="absolute inset-0" count={particleCount ?? 36} />}

      {/* Depth 7 — film grain on top */}
      {layers.noise && <NoiseOverlay className="absolute inset-0" />}
    </div>
  );
}

/** Translates children by a fraction of the cursor position (depth illusion). */
function DepthLayer({
  factor,
  className,
  children,
  reduceMotion,
}: {
  factor: number;
  className?: string;
  children: React.ReactNode;
  reduceMotion: boolean | null;
}) {
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 42, damping: 26, mass: 0.9 });
  const y = useSpring(my, { stiffness: 42, damping: 26, mass: 0.9 });

  React.useEffect(() => {
    if (reduceMotion) return;
    const onMove = (e: MouseEvent) => {
      mx.set((e.clientX / window.innerWidth - 0.5) * 32 * factor);
      my.set((e.clientY / window.innerHeight - 0.5) * 32 * factor);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [reduceMotion, factor, mx, my]);

  if (reduceMotion) {
    return <div aria-hidden className={className}>{children}</div>;
  }

  return (
    <motion.div aria-hidden className={cn("will-change-transform", className)} style={{ x, y }}>
      {children}
    </motion.div>
  );
}

/** Soft radial light that trails the cursor. */
function MouseSpotlight({ reduceMotion }: { reduceMotion: boolean | null }) {
  const mx = useMotionValue(-640);
  const my = useMotionValue(-640);
  const x = useSpring(mx, { stiffness: 60, damping: 22, mass: 0.6 });
  const y = useSpring(my, { stiffness: 60, damping: 22, mass: 0.6 });

  React.useEffect(() => {
    if (reduceMotion) return;
    const onMove = (e: MouseEvent) => {
      mx.set(e.clientX - 480);
      my.set(e.clientY - 480);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [reduceMotion, mx, my]);

  if (reduceMotion) return null;

  return (
    <motion.div
      aria-hidden
      style={{ x, y }}
      className="pointer-events-none absolute left-0 top-0 hidden size-[960px] rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--primary)/0.05),transparent_60%)] md:block"
    />
  );
}
