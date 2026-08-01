"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, PanelLeftClose } from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/shared/logo";
import { Icon } from "@/components/shared/icons";
import { navGroups } from "@/lib/navigation";
import { useSidebar } from "@/stores/sidebar";
import { Button } from "@/components/ui/button";
import { useSession } from "@/stores/session";
import { Badge } from "@/components/ui/badge";

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle } = useSidebar();
  const { user } = useSession();

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 252 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="hidden shrink-0 flex-col border-r border-border/80 bg-background/60 backdrop-blur-2xl lg:flex"
    >
      <div className={cn("flex h-14 items-center gap-2 border-b border-border/60 px-4", collapsed && "justify-center px-0")}>
        {!collapsed && <Logo />}
        <Button variant="ghost" size="icon-sm" className={cn("ml-auto text-muted-foreground", collapsed && "ml-0")} onClick={toggle} aria-label="Collapse sidebar">
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto p-3 no-scrollbar">
        {navGroups.map((group) => (
          <div key={group.group} className="space-y-1">
            {!collapsed && (
              <p className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
                {group.group}
              </p>
            )}
            {group.items.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors",
                    collapsed && "justify-center px-0",
                    active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="sidebar-active"
                      className="absolute inset-0 rounded-xl bg-primary/10 ring-1 ring-inset ring-primary/25 shadow-[0_0_24px_-6px_hsl(var(--primary)/0.4)]"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <span className="relative flex size-5 items-center justify-center">
                    <Icon name={item.icon} className={cn("h-[18px] w-[18px] transition-transform duration-200", !active && "group-hover:scale-110")} />
                  </span>
                  {!collapsed && <span className="relative">{item.label}</span>}
                  {!collapsed && item.badge && (
                    <Badge variant="gradient" className="relative ml-auto px-1.5 py-0 text-[10px]">
                      {item.badge}
                    </Badge>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-border/60 p-3">
        <Link
          href="/chat"
          className={cn(
            "group relative flex items-center gap-3 overflow-hidden rounded-xl border border-primary/30 bg-gradient-to-r from-primary/15 via-primary/8 to-transparent p-2.5 text-sm font-medium text-primary transition-colors hover:border-primary/50",
            collapsed && "justify-center px-0",
          )}
        >
          <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          <Plus className="relative h-4 w-4" />
          {!collapsed && <span className="relative">New automation</span>}
        </Link>
        {!collapsed && user && (
          <p className="mt-3 truncate px-1 text-[11px] text-muted-foreground/70">
            {user.org} · <span className="capitalize">{user.role}</span>
          </p>
        )}
      </div>
    </motion.aside>
  );
}
