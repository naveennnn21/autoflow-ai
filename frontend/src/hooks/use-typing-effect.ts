"use client";

import { useEffect, useRef, useState } from "react";

export function useTypingEffect(text: string, speed = 16) {
  const [display, setDisplay] = useState("");
  const [done, setDone] = useState(false);
  const idx = useRef(0);

  useEffect(() => {
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
  }, [text, speed]);

  return { display, done };
}
