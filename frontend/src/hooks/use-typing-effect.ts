"use client";

import { useEffect, useRef, useState } from "react";

interface UseTypingEffectOptions {
  enabled?: boolean;
  speed?: number;
}

export function useTypingEffect(
  text: string,
  options?: UseTypingEffectOptions | number,
) {
  // Support both old (number) and new (options object) signatures
  const speed = typeof options === "number" ? options : (options?.speed ?? 16);
  const enabled = typeof options === "number" ? true : (options?.enabled ?? true);

  const [display, setDisplay] = useState("");
  const [done, setDone] = useState(false);
  const idx = useRef(0);

  useEffect(() => {
    if (!enabled) {
      setDisplay(text);
      setDone(true);
      return;
    }
    idx.current = 0;
    setDisplay("");
    setDone(false);
    const interval = setInterval(() => {
      idx.current += 1;
      setDisplay(text.slice(0, idx.current));
      if (idx.current >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed, enabled]);

  return { display, done };
}