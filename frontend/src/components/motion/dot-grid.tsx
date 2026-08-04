"use client";

import { cn } from "@/lib/utils";

interface DotGridProps {
  className?: string;
  dense?: boolean;
}

export function DotGrid({ className, dense = false }: DotGridProps) {
  return <div aria-hidden className={cn("pointer-events-none absolute inset-0", dense ? "bg-dots" : "bg-dots-lg", className)} />;
}
