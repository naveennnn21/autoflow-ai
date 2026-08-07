"use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Check, Plug, RefreshCw, Star } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Icon } from "@/components/shared/icons";
import { ConnectorHealthBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/shared/skeleton";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { connectorsApi } from "@/lib/api/connectors";
import { formatCompact } from "@/lib/utils";

export default function ConnectorDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const [slug, setSlug] = React.useState<string | null>(null);
  const [installed, setInstalled] = React.useState(false);

  React.useEffect(() => {
    void params.then((p) => setSlug(p.slug));
  }, [params]);

  const { data: connector, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.connector(slug ?? ""),
    queryFn: () => connectorsApi.get(slug ?? ""),
    enabled: !!slug,
  });

  if (isError && !isLoading) {
    return (
      <EmptyState
        title="Couldn't load this connector"
        description="The connector registry API is unreachable or this connector does not exist."
        action={
          <Button variant="outline" size="sm" className="gap-2" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Retry
          </Button>
        }
      />
    );
  }

  if (isLoading || !slug) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-40" />
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <Skeleton className="h-16 w-16 rounded-2xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-full max-w-xl" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!connector) {
    notFound();
  }

  const install = () => {
    setInstalled(true);
    toast.success(`${connector.name} connected`, {
      description: `Scopes requested: ${connector.scopes.slice(0, 3).join(", ") || "read-only"}`,
    });
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link href="/marketplace">
          <ArrowLeft className="h-4 w-4" /> Back to marketplace
        </Link>
      </Button>

      <Card className="overflow-hidden">
        <div className="relative h-24 bg-gradient-to-r from-brand-purple/20 via-brand-blue/15 to-brand-cyan/20" />
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <span
              className="flex h-16 w-16 -mt-10 items-center justify-center rounded-2xl border border-border bg-card shadow-soft"
              style={{ color: connector.color }}
            >
              <Icon name={connector.logo} className="h-7 w-7" />
            </span>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight">{connector.name}</h1>
                {connector.rating > 0 && (
                  <span className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Star className="h-4 w-4 fill-amber-400 text-amber-400" /> {connector.rating}
                  </span>
                )}
                {connector.verified && <Badge variant="success">Verified</Badge>}
                <ConnectorHealthBadge health={connector.health} />
              </div>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{connector.description}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge variant="secondary">{connector.category}</Badge>
                <Badge variant="secondary">{connector.auth}</Badge>
                <Badge variant="secondary">Rate limit: {connector.rateLimit}</Badge>
                {connector.installs > 0 && (
                  <Badge variant="secondary">{formatCompact(connector.installs)} installs</Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {installed || connector.installed ? (
                <Badge variant="success"><Check className="h-3.5 w-3.5" /> Connected</Badge>
              ) : (
                <Button onClick={install}>
                  <Plug className="h-4 w-4" /> Connect
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="actions">Actions ({connector.actions.length})</TabsTrigger>
          <TabsTrigger value="triggers">Triggers ({connector.triggers.length})</TabsTrigger>
          <TabsTrigger value="authentication">Authentication</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Auth type", value: connector.auth.toUpperCase() },
              { label: "Rate limit", value: connector.rateLimit },
              { label: "Installs", value: connector.installs > 0 ? formatCompact(connector.installs) : "—" },
              { label: "Version", value: connector.version ?? "1.0.0" },
            ].map((s) => (
              <Card key={s.label}>
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="mt-1 text-lg font-semibold">{s.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="actions" className="mt-4 space-y-2">
          {connector.actions.length === 0 ? (
            <EmptyState title="No actions" description="This connector exposes triggers only." />
          ) : (
            connector.actions.map((a) => (
              <Card key={a.id}>
                <CardContent className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="text-sm font-medium">{a.name}</p>
                    <p className="text-xs text-muted-foreground">{a.description}</p>
                  </div>
                  <div className="flex gap-1.5">
                    <Badge variant="secondary" className="text-[10px]">{a.kind}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="triggers" className="mt-4 space-y-2">
          {connector.triggers.length === 0 ? (
            <EmptyState title="No triggers" description="This connector can be started manually or via the API." />
          ) : (
            connector.triggers.map((t) => (
              <Card key={t.id}>
                <CardContent className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="text-sm font-medium">{t.name}</p>
                    <p className="text-xs text-muted-foreground">{t.description}</p>
                  </div>
                  <Badge variant="secondary" className="text-[10px]">{t.kind}</Badge>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="authentication" className="mt-4">
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold">Authentication — {connector.auth.toUpperCase()}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                AutoFlow manages the full auth lifecycle — authorization URL, token exchange, automatic refresh, and secure credential storage.
              </p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {connector.scopes.length === 0 ? (
                  <span className="text-sm text-muted-foreground">No scopes required for this connector.</span>
                ) : (
                  connector.scopes.map((s) => (
                    <Badge key={s} variant="outline" className="font-mono text-[11px]">{s}</Badge>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
