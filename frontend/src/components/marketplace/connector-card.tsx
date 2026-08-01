"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Check, Plug, Star } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/shared/icons";
import { ConnectorHealthBadge } from "@/components/shared/status-badge";
import { formatCompact } from "@/lib/utils";
import type { Connector } from "@/types";

export function ConnectorCard({ connector, onInstall }: { connector: Connector; onInstall?: (c: Connector) => void }) {
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 260, damping: 22 }}>
      <Card className="card-hover group relative h-full overflow-hidden border-border/70">
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-25"
          style={{ background: connector.color }}
        />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
        <CardContent className="flex h-full flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <span
              className="flex h-11 w-11 items-center justify-center rounded-xl border border-border/70 bg-background/60 shadow-[inset_0_1px_0_0_hsl(var(--foreground)/0.05)] transition-shadow group-hover:shadow-[0_0_20px_-6px_var(--tw-shadow-color)]"
              style={{ color: connector.color, "--tw-shadow-color": connector.color } as React.CSSProperties}
            >
              <Icon name={connector.logo} className="h-5 w-5" />
            </span>
            <div className="flex items-center gap-1.5">
              {connector.verified && <Badge variant="success" className="text-[10px]">Verified</Badge>}
              <ConnectorHealthBadge health={connector.health} />
            </div>
          </div>

          <div className="mt-4">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{connector.name}</h3>
              <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
                <Star className="h-3 w-3 fill-warning text-warning" />
                {connector.rating}
              </span>
            </div>
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{connector.description}</p>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="text-[10px]">{connector.category}</Badge>
            <Badge variant="secondary" className="text-[10px]">{connector.auth}</Badge>
            <Badge variant="secondary" className="text-[10px]">{connector.rateLimit}</Badge>
          </div>

          <div className="mt-auto flex items-center justify-between pt-4">
            <span className="text-xs text-muted-foreground">{formatCompact(connector.installs)} installs</span>
            <div className="flex items-center gap-1.5">
              {connector.installed ? (
                <Badge variant="success">
                  <Check className="h-3 w-3" /> Installed
                </Badge>
              ) : (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    onInstall?.(connector);
                  }}
                  className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-primary to-secondary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-[0_4px_16px_-6px_hsl(var(--primary)/0.6)] transition-all hover:brightness-110 active:scale-95"
                >
                  <Plug className="h-3 w-3" /> Install
                </button>
              )}
            </div>
          </div>

          <Link
            href={`/marketplace/${connector.slug}`}
            className="mt-4 flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-all duration-300 group-hover:translate-x-0.5 group-hover:opacity-100"
          >
            View details <ArrowRight className="h-3 w-3" />
          </Link>
        </CardContent>
      </Card>
    </motion.div>
  );
}
