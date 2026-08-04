"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface WordRevealProps {
  text: string;
  className?: string;
  /** Delay before the reveal starts (seconds) */
  delay?: number;
  /** Stagger between words (seconds) */
  stagger?: number;
  as?: "h1" | "h2" | "h3" | "p" | "span" | "div";
}

/**
 * Premium cinematic word-by-word text reveal.
 * Each word rises from below with a soft blur, staggered in sequence.
 */
export function WordReveal({ text, className, delay = 0, stagger = 0.045, as = "span" }: WordRevealProps) {
  const reduceMotion = useReducedMotion();
  const words = text.split(" ");

  if (reduceMotion) {
    const Comp = as as "span";
    return <Comp className={className}>{text}</Comp>;
  }

  const Comp = motion[as] as typeof motion.span;

  return (
    <Comp
      className={cn("inline-block", className)}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ staggerChildren: stagger, delayChildren: delay }}
      aria-label={text}
    >
      {words.map((word, i) => (
        <span key={i} aria-hidden className="inline-block overflow-hidden pb-[0.12em] -mb-[0.12em] align-bottom">
          <motion.span
            className="inline-block will-change-transform"
            variants={{
              hidden: { opacity: 0, y: "110%", rotate: 4, filter: "blur(6px)" },
              visible: {
                opacity: 1,
                y: "0%",
                rotate: 0,
                filter: "blur(0px)",
                transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
              },
            }}
          >
            {word}
            {i < words.length - 1 ? "\u00A0" : ""}
          </motion.span>
        </span>
      ))}
    </Comp>
  );
}
