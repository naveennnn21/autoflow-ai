import type { NavItem } from "@/types";

export const navGroups: { group: string; items: NavItem[] }[] = [
  {
    group: "Workspace",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: "layout-dashboard" },
      { label: "AI Copilot", href: "/chat", icon: "sparkles", badge: "New" },
      { label: "Workflows", href: "/workflows", icon: "workflow" },
    ],
  },
  {
    group: "Platform",
    items: [
      { label: "Marketplace", href: "/marketplace", icon: "boxes" },
      { label: "Analytics", href: "/analytics", icon: "chart-line" },
    ],
  },
  {
    group: "Organization",
    items: [{ label: "Settings", href: "/settings", icon: "settings" }],
  },
];

export const commandShortcuts = [
  { key: "mod+k", label: "Open command palette" },
  { key: "g then d", label: "Go to dashboard" },
  { key: "g then w", label: "Go to workflows" },
  { key: "g then m", label: "Go to marketplace" },
  { key: "?", label: "Show shortcuts" },
];
