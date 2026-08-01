"use client";

import { cn } from "@/lib/utils";

interface GradientOrbProps {
  className?: string;
  color?: "primary" | "secondary" | "accent" | "success";
}

const palettes: Record<string, string> = {
  primary: "bg-[radial-gradient(circle_at_center,hsl(var(--primary)/0.5),transparent_65%)]",
  secondary: "bg-[radial-gradient(circle_at_center,hsl(var(--secondary)/0.4),transparent_65%)]",
  accent: "bg-[radial-gradient(circle_at_center,hsl(var(--accent)/0.45),transparent_65%)]",
  success: "bg-[radial-gradient(circle_at_center,hsl(var(--success)/0.35),transparent_65%)]",
};

export function GradientOrb({ className, color = "primary" }: GradientOrbProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute rounded-full blur-3xl animate-pulse-glow",
        palettes[color],
        className,
      )}
    />
  );
}
