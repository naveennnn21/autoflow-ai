"use client";

import * as React from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";

/** Interactive elements the ring reacts to. */
const INTERACTIVE_SELECTOR =
  "a, button, input, textarea, select, summary, label, [role='button'], [role='link'], [role='menuitem'], [role='tab'], [data-cursor='pointer']";

const isInteractive = (target: EventTarget | null) =>
  target instanceof Element && Boolean(target.closest?.(INTERACTIVE_SELECTOR));

/**
 * Full custom cursor — a precise dot plus a spring-trailing ring.
 *
 * - Ring grows over interactive elements (links, buttons, inputs…)
 * - Both compress slightly on press, then bounce back
 * - Native cursor is hidden while active (fine pointers only)
 * - Fades out when the pointer leaves the window
 * - Fully disabled under prefers-reduced-motion and on touch devices,
 *   restoring the native cursor
 */
export function CustomCursor() {
  const reduceMotion = useReducedMotion();
  const [enabled, setEnabled] = React.useState(false);

  // Dot tracks the pointer exactly; ring trails behind on a spring.
  const dotX = useMotionValue(-100);
  const dotY = useMotionValue(-100);
  const ringX = useSpring(dotX, { stiffness: 260, damping: 24, mass: 0.5 });
  const ringY = useSpring(dotY, { stiffness: 260, damping: 24, mass: 0.5 });

  // Hover + press scaling, spring-damped so it never snaps.
  const hover = useMotionValue(1);
  const pressed = useMotionValue(1);
  const ringScale = useSpring(hover, { stiffness: 320, damping: 26 });
  const dotScale = useSpring(pressed, { stiffness: 400, damping: 30 });

  // Fade in on first move, fade out when leaving the window.
  const shown = useMotionValue(0);
  const ringOpacity = useSpring(shown, { stiffness: 260, damping: 28 });
  const dotOpacity = useSpring(shown, { stiffness: 520, damping: 34 });

  const overInteractive = React.useRef(false);

  React.useEffect(() => {
    if (reduceMotion) return;
    const finePointer = window.matchMedia("(pointer: fine)").matches;
    if (!finePointer) return;
    setEnabled(true);
    document.documentElement.classList.add("has-custom-cursor");

    const onMove = (e: MouseEvent) => {
      dotX.set(e.clientX);
      dotY.set(e.clientY);
      shown.set(1);
    };

    const onOver = (e: MouseEvent) => {
      const interactive = isInteractive(e.target);
      if (interactive !== overInteractive.current) {
        overInteractive.current = interactive;
        hover.set(interactive ? 1.85 : 1);
      }
    };

    const onDown = () => pressed.set(0.82);
    const onUp = () => pressed.set(1);
    const onLeave = () => shown.set(0);

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseover", onOver, { passive: true });
    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);
    document.documentElement.addEventListener("mouseleave", onLeave);

    return () => {
      document.documentElement.classList.remove("has-custom-cursor");
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onOver);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
      document.documentElement.removeEventListener("mouseleave", onLeave);
    };
  }, [reduceMotion, dotX, dotY, hover, pressed, shown]);

  if (!enabled) return null;

  return (
    <>
      {/* Trailing ring — mix-blend-difference inverts over any surface */}
      <motion.div
        aria-hidden
        style={{ x: ringX, y: ringY, opacity: ringOpacity, scale: ringScale }}
        className="pointer-events-none fixed left-0 top-0 z-[9999] -ml-5 -mt-5 h-10 w-10 rounded-full border-[1.5px] border-white/90 mix-blend-difference will-change-transform"
      />
      {/* Precise dot */}
      <motion.div
        aria-hidden
        style={{ x: dotX, y: dotY, opacity: dotOpacity, scale: dotScale }}
        className="pointer-events-none fixed left-0 top-0 z-[9999] -ml-[3px] -mt-[3px] h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_10px_hsl(var(--primary)/0.9)] will-change-transform"
      />
    </>
  );
}
