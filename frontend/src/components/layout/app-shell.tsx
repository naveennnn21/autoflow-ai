"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { useHotkey } from "@/hooks/use-keyboard";
import { useCommand } from "@/stores/command";
import { useSession } from "@/stores/session";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";
import { CursorGlow } from "@/components/motion/cursor-glow";
import { ScrollProgress } from "@/components/motion/scroll-progress";
import { PageTransition } from "@/components/motion/page-transition";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { toggle } = useCommand();
  const hydrate = useSession((s) => s.hydrate);

  useHotkey("mod+k", (e) => {
    e.preventDefault();
    toggle();
  });

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  return (
    <div className="relative flex min-h-screen">
      <CursorGlow />
      <ScrollProgress />
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="relative flex-1 p-4 sm:p-6 lg:p-8">
          <AnimatePresence mode="wait" initial={false}>
            <PageTransition key={pathname} className="h-full">
              {children}
            </PageTransition>
          </AnimatePresence>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
