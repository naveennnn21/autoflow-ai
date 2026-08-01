"use client";

import {
  Activity,
  BarChart3,
  Bot,
  Boxes,
  Brain,
  Database,
  GitBranch,
  Gauge,
  HardDrive,
  LayoutDashboard,
  Mail,
  MessageSquare,
  Plug,
  Rocket,
  Settings,
  ShoppingBag,
  Slack,
  Sparkles,
  Table,
  Users,
  Wand2,
  Workflow,
  Zap,
  type LucideIcon,
} from "lucide-react";

const map: Record<string, LucideIcon> = {
  "layout-dashboard": LayoutDashboard,
  sparkles: Sparkles,
  workflow: Workflow,
  boxes: Boxes,
  "chart-line": BarChart3,
  settings: Settings,
  zap: Zap,
  rocket: Rocket,
  brain: Brain,
  wand2: Wand2,
  bot: Bot,
  plug: Plug,
  gauge: Gauge,
  mail: Mail,
  slack: Slack,
  github: GitBranch,
  notion: Bot,
  stripe: Zap,
  "shopping-bag": ShoppingBag,
  "message-square": MessageSquare,
  "hard-drive": HardDrive,
  table: Table,
  "git-branch": GitBranch,
  database: Database,
  users: Users,
  activity: Activity,
};

export function Icon({ name, className, style }: { name: string; className?: string; style?: React.CSSProperties }) {
  const C = map[name] ?? Sparkles;
  return <C className={className} style={style} />;
}

export { map as iconMap };
