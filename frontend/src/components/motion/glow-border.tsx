"use client";

import { cn } from "@/lib/utils";

export function GlowBorder({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <div className={cn("gradient-border rounded-xl", className)}>{children}</div>
  );
}
