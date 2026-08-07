"use client";

import * as React from "react";
import { toast } from "sonner";
import { Key, Bell, Building2, Monitor, RefreshCw, Trash2, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useSession } from "@/stores/session";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { organizationsApi } from "@/lib/api/organizations";
import { apiKeysApi } from "@/lib/api/api-keys";
import { timeAgo } from "@/lib/utils";
import type { Organization } from "@/types";

function randomPrefix(): string {
  const a = Math.random().toString(36).slice(2, 10);
  const b = Math.random().toString(36).slice(2, 6);
  return `af_${a}_${b}`;
}

export default function SettingsPage() {
  const user = useSession((s) => s.user);
  const orgId = useSession((s) => s.orgId);
  const queryClient = useQueryClient();

  // --- organization -------------------------------------------------------
  const orgQuery = useQuery({
    queryKey: queryKeys.organizations,
    queryFn: () => organizationsApi.list({ page: 1, page_size: 50 }),
    enabled: !!orgId,
  });
  const org = React.useMemo<Organization | undefined>(() => {
    const items = orgQuery.data?.items ?? [];
    return items.find((o) => o.id === orgId) ?? items[0];
  }, [orgQuery.data, orgId]);

  const orgMutation = useMutation({
    mutationFn: (payload: { name?: string; slug?: string; settings?: Record<string, unknown> }) =>
      organizationsApi.update(org!.id, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.organizations, (old: unknown) => {
        const prev = (old ?? {}) as { items?: Organization[] };
        return {
          ...prev,
          items: (prev.items ?? []).map((o) => (o.id === updated.id ? updated : o)),
        };
      });
    },
  });

  // --- api keys -----------------------------------------------------------
  const keysQuery = useQuery({
    queryKey: queryKeys.apiKeys,
    queryFn: () => apiKeysApi.list({ page: 1, page_size: 50 }),
  });
  const createKey = useMutation({
    mutationFn: (name: string) =>
      apiKeysApi.create({
        organization_id: orgId ?? "",
        user_id: user?.id ?? "",
        name,
        key_prefix: randomPrefix(),
      }),
    onSuccess: (key) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
      toast.success("API key created", {
        description: `Prefix: ${key.key_prefix}… (full secret shown once at creation)`,
        duration: 8000,
      });
    },
    onError: (err) => toast.error("Could not create API key", { description: err instanceof Error ? err.message : undefined }),
  });
  const deleteKey = useMutation({
    mutationFn: (id: string) => apiKeysApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
      toast.success("API key revoked");
    },
  });

  const [keyName, setKeyName] = React.useState("");

  // --- helpers ------------------------------------------------------------
  const settings = (org?.settings ?? {}) as Record<string, unknown>;
  const notifications = (settings.notifications ?? {}) as Record<string, boolean>;
  const preferences = (settings.preferences ?? {}) as Record<string, boolean>;

  const patchSettings = (section: string, patch: Record<string, boolean>) => {
    if (!org) return;
    const current = (settings[section] ?? {}) as Record<string, boolean>;
    const next: Record<string, unknown> = {
      ...settings,
      [section]: { ...current, ...patch },
    };
    orgMutation.mutate(
      { settings: next },
      {
        onSuccess: () => toast.success("Preferences saved"),
        onError: () => toast.error("Could not save preferences"),
      },
    );
  };

  const saveOrgProfile = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!org) return;
    const fd = new FormData(e.currentTarget);
    orgMutation.mutate(
      {
        name: String(fd.get("org") ?? org.name),
        slug: String(fd.get("slug") ?? org.slug),
      },
      {
        onSuccess: () => toast.success("Organization profile saved"),
        onError: () => toast.error("Could not save organization profile"),
      },
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Settings" description="Manage your organization, team, and workspace preferences." />

      <Tabs defaultValue="organization">
        <TabsList className="flex-wrap">
          <TabsTrigger value="organization"><Building2 className="h-3.5 w-3.5" /> Organization</TabsTrigger>
          <TabsTrigger value="api"><Key className="h-3.5 w-3.5" /> API keys</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-3.5 w-3.5" /> Notifications</TabsTrigger>
          <TabsTrigger value="preferences"><Monitor className="h-3.5 w-3.5" /> Preferences</TabsTrigger>
        </TabsList>

        <TabsContent value="organization" className="mt-4 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Organization profile</CardTitle>
              <CardDescription>Shown across your workspace and invoices.</CardDescription>
            </CardHeader>
            <CardContent>
              {orgQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : !org ? (
                <EmptyState title="No organization found" description="Your account has no workspace yet." />
              ) : (
                <form onSubmit={saveOrgProfile} className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="org">Organization name</Label>
                    <Input id="org" name="org" defaultValue={org.name} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="slug">Workspace slug</Label>
                    <Input id="slug" name="slug" defaultValue={org.slug} />
                  </div>
                  <div className="sm:col-span-2">
                    <Button type="submit" disabled={orgMutation.isPending}>
                      {orgMutation.isPending ? "Saving..." : "Save changes"}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Members</CardTitle>
              <CardDescription>Who can access this workspace.</CardDescription>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {user ? (
                <div className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{user.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <Badge variant={user.role === "admin" ? "default" : "secondary"}>{user.role}</Badge>
                </div>
              ) : null}
              <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5" />
                Invite &amp; member management ships with the team endpoints in the next phase.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api" className="mt-4 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>API keys</CardTitle>
              <CardDescription>Keys inherit your role permissions. Treat them like passwords.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  placeholder="Key name (e.g. Production)"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  className="max-w-xs"
                />
                <Button
                  onClick={() => {
                    if (!keyName.trim()) {
                      toast.error("Give your key a name first");
                      return;
                    }
                    createKey.mutate(keyName.trim());
                    setKeyName("");
                  }}
                  disabled={createKey.isPending || !orgId}
                >
                  <Key className="h-4 w-4" /> Create API key
                </Button>
              </div>
              <div className="divide-y divide-border rounded-lg border border-border">
                {keysQuery.isLoading ? (
                  <div className="space-y-2 p-4">
                    {Array.from({ length: 2 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (keysQuery.data?.items ?? []).length === 0 ? (
                  <p className="p-6 text-center text-sm text-muted-foreground">
                    No API keys yet. Create one to access the API programmatically.
                  </p>
                ) : (
                  (keysQuery.data?.items ?? []).map((k) => (
                    <div key={k.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">{k.name}</p>
                        <p className="truncate font-mono text-[11px] text-muted-foreground">
                          {k.key_prefix}••••••••••••••
                        </p>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {k.last_used_at ? `last used ${timeAgo(k.last_used_at)}` : "never used"}
                      </span>
                      <Badge variant={k.is_active === false ? "secondary" : "success"}>
                        {k.is_active === false ? "revoked" : "active"}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Revoke ${k.name}`}
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => deleteKey.mutate(k.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Notification preferences</CardTitle>
              <CardDescription>Choose how you hear about workflow activity. Stored on your organization.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {orgQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                [
                  { key: "failures", label: "Workflow failures", desc: "Alert me immediately when a workflow fails after retries" },
                  { key: "digest", label: "Daily digest", desc: "Summary of runs, failures, and cost every morning" },
                  { key: "connectorHealth", label: "Connector health", desc: "Notify when a connector degrades or goes down" },
                  { key: "weeklyUpdates", label: "Weekly product updates", desc: "New connectors, features, and improvements" },
                ].map((n) => (
                  <div key={n.key} className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium">{n.label}</p>
                      <p className="text-xs text-muted-foreground">{n.desc}</p>
                    </div>
                    <Switch
                      checked={notifications[n.key] ?? n.key === "failures"}
                      onCheckedChange={(v) => patchSettings("notifications", { [n.key]: v })}
                      disabled={orgMutation.isPending}
                    />
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Workspace preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {orgQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                [
                  { key: "reduceMotion", label: "Reduce motion", desc: "Minimize animations across the product" },
                  { key: "defaultLight", label: "Default to light theme", desc: "Override the system preference" },
                  { key: "confirmDestructive", label: "Confirm before destructive actions", desc: "Require confirmation for deletes and pauses" },
                ].map((p) => (
                  <div key={p.key} className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium">{p.label}</p>
                      <p className="text-xs text-muted-foreground">{p.desc}</p>
                    </div>
                    <Switch
                      checked={preferences[p.key] ?? p.key === "confirmDestructive"}
                      onCheckedChange={(v) => patchSettings("preferences", { [p.key]: v })}
                      disabled={orgMutation.isPending}
                    />
                  </div>
                ))
              )}
              <Button variant="ghost" size="sm" className="gap-2" onClick={() => void queryClient.invalidateQueries({ queryKey: queryKeys.organizations })}>
                <RefreshCw className="h-3.5 w-3.5" /> Reload settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
