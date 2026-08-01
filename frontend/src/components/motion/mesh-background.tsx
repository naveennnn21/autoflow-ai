"use client";

import { cn } from "@/lib/utils";

interface MeshBackgroundProps {
  className?: string;
  intensity?: "subtle" | "medium" | "strong";
}

const opacities = {
  subtle: "opacity-40",
  medium: "opacity-60",
  strong: "opacity-80",
};

export function MeshBackground({ className, intensity = "medium" }: MeshBackgroundProps) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className={cn("absolute inset-0 mesh-bg animate-mesh", opacities[intensity])} />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,transparent_0%,hsl(var(--background))_70%)]" />
    </div>
  );
}
