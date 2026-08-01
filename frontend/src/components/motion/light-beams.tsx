"use client";

import { cn } from "@/lib/utils";

interface LightBeamsProps {
  className?: string;
}

export function LightBeams({ className }: LightBeamsProps) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className="absolute top-0 left-1/4 h-full w-px bg-gradient-to-b from-transparent via-primary/20 to-transparent" />
      <div className="absolute top-0 left-1/2 h-full w-px bg-gradient-to-b from-transparent via-secondary/15 to-transparent" />
      <div className="absolute top-0 left-3/4 h-full w-px bg-gradient-to-b from-transparent via-accent/20 to-transparent" />
      <div
        className="absolute top-[-20%] left-[18%] h-[60%] w-24 rotate-[18deg] bg-gradient-to-r from-transparent via-primary/10 to-transparent blur-md animate-beam"
        style={{ animationDelay: "0s" }}
      />
      <div
        className="absolute top-[10%] left-[58%] h-[50%] w-32 rotate-[-14deg] bg-gradient-to-r from-transparent via-secondary/10 to-transparent blur-md animate-beam"
        style={{ animationDelay: "1.1s" }}
      />
      <div
        className="absolute top-[-10%] left-[82%] h-[55%] w-24 rotate-[22deg] bg-gradient-to-r from-transparent via-accent/10 to-transparent blur-md animate-beam"
        style={{ animationDelay: "2.1s" }}
      />
    </div>
  );
}
