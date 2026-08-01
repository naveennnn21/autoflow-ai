"use client";

import { cn } from "@/lib/utils";

export function AuroraBackground({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className="absolute -left-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-brand-purple/25 blur-[120px] animate-aurora" />
      <div className="absolute -right-40 top-10 h-[30rem] w-[30rem] rounded-full bg-brand-cyan/20 blur-[120px] animate-aurora [animation-delay:3s]" />
      <div className="absolute bottom-0 left-1/3 h-[28rem] w-[28rem] rounded-full bg-brand-blue/20 blur-[130px] animate-aurora [animation-delay:6s]" />
    </div>
  );
}
