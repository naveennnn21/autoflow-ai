"use client";

import { useEffect } from "react";

export type KeyCombo = string;

export function useHotkey(combo: KeyCombo, handler: (e: KeyboardEvent) => void, deps: unknown[] = []) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const parts = combo.split("+").map((p) => p.trim().toLowerCase());
      const needsMod = parts.includes("mod");
      const key = parts.filter((p) => p !== "mod").join("");
      const matches =
        (!needsMod || mod) &&
        (needsMod || !mod) &&
        e.key.toLowerCase() === key;
      if (matches) handler(e);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, combo]);
}
