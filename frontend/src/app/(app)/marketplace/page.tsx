"use client";

import * as React from "react";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { ConnectorCard } from "@/components/marketplace/connector-card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { connectors } from "@/lib/mock-connectors";
import { cn } from "@/lib/utils";
import type { Connector } from "@/types";

export default function MarketplacePage() {
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState<string>("All");
  const [installed, setInstalled] = React.useState<Set<string>>(new Set(connectors.filter((c) => c.installed).map((c) => c.id)));

  const categories = React.useMemo(() => {
    const set = new Set(connectors.map((c) => c.category));
    return ["All", ...Array.from(set).sort()];
  }, []);

  const filtered = React.useMemo(() => {
    const q = query.toLowerCase();
    return connectors.filter((c) => {
      const matchesCategory = category === "All" || c.category === category;
      const matchesQuery =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        (c.tags ?? []).some((t) => t.toLowerCase().includes(q));
      return matchesCategory && matchesQuery;
    });
  }, [query, category]);

  const install = (c: Connector) => {
    setInstalled((prev) => new Set(prev).add(c.id));
    toast.success(`${c.name} connected`, {
      description: `OAuth flow complete · scopes: ${c.scopes.slice(0, 2).join(", ")}`,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Connector Marketplace"
        description="200+ integrations. One OAuth flow. Automatic token refresh and per-connector rate limits."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search connectors..."
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
                category === cat
                  ? "border-transparent bg-primary text-primary-foreground shadow-glow"
                  : "border-border bg-card text-muted-foreground hover:text-foreground",
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="secondary">{filtered.length} connectors</Badge>
        {installed.size > 0 && <Badge variant="success">{installed.size} connected</Badge>}
      </div>

      <StaggerGroup className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((c) => (
          <StaggerItem key={c.id}>
            <ConnectorCard connector={{ ...c, installed: installed.has(c.id) }} onInstall={install} />
          </StaggerItem>
        ))}
      </StaggerGroup>
    </div>
  );
}
