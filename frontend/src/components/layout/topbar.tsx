"use client";

import { Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCommand } from "@/stores/command";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";
import { useSidebar } from "@/stores/sidebar";
import { PanelLeft } from "lucide-react";

export function Topbar() {
  const { setOpen } = useCommand();
  const { toggle } = useSidebar();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border/60 bg-background/70 px-4 backdrop-blur-2xl">
      <Button variant="ghost" size="icon-sm" className="lg:hidden" onClick={toggle} aria-label="Toggle sidebar">
        <PanelLeft className="h-4 w-4" />
      </Button>
      <button
        onClick={() => setOpen(true)}
        className="group flex h-9 w-full max-w-sm items-center gap-2 rounded-xl border border-border bg-muted/30 px-3 text-sm text-muted-foreground shadow-[inset_0_1px_0_0_hsl(var(--foreground)/0.04)] transition-all hover:border-primary/40 hover:bg-muted/40 hover:shadow-[0_0_24px_-8px_hsl(var(--primary)/0.5)] focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Search className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
        <span>Search anything...</span>
        <kbd className="ml-auto rounded-md border border-border bg-background/60 px-1.5 py-0.5 text-[10px] font-medium">⌘K</kbd>
      </button>
      <div className="ml-auto flex items-center gap-1">
        <Button variant="ghost" size="icon" aria-label="Notifications" className="relative text-muted-foreground">
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 size-1.5 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
        </Button>
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
