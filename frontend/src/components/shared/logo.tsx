"use client";

import Link from "next/link";
import { Workflow } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("group inline-flex items-center gap-2", className)}>
      <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-purple to-brand-cyan shadow-glow transition-transform group-hover:scale-105">
        <Workflow className="h-4.5 w-4.5 h-[18px] w-[18px] text-white" />
      </span>
      <span className="text-[17px] font-semibold tracking-tight">
        AutoFlow<span className="gradient-text"> AI</span>
      </span>
    </Link>
  );
}
