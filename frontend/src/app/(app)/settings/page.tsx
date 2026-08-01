"use client";

import { toast } from "sonner";
import { Key, Bell, Building2, Monitor } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useSession } from "@/stores/session";
import * as React from "react";

export default function SettingsPage() {
  const user = useSession((s) => s.user);

  const save = (label: string) => {
    toast.success(`${label} saved`);
  };

  const createKey = () => {
    const key = `af_${Math.random().toString(36).slice(2, 14)}_${Math.random().toString(36).slice(2, 10)}`;
    toast.success("API key created", {
      description: key,
      duration: 12000,
    });
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
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="org">Organization name</Label>
                <Input id="org" defaultValue={user?.org ?? "Acme Corp"} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="slug">Workspace slug</Label>
                <Input id="slug" defaultValue="acme-corp" />
              </div>
              <div className="sm:col-span-2">
                <Button onClick={() => save("Organization profile")}>Save changes</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Members</CardTitle>
              <CardDescription>Manage who can access this workspace.</CardDescription>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {[
                { name: "Ava Torres", email: "ava@acme.com", role: "admin" },
                { name: "Priya Sharma", email: "priya@acme.com", role: "member" },
                { name: "Jonas Weber", email: "jonas@acme.com", role: "member" },
              ].map((m) => (
                <div key={m.email} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{m.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{m.email}</p>
                  </div>
                  <Badge variant={m.role === "admin" ? "default" : "secondary"}>{m.role}</Badge>
                </div>
              ))}
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
              <Button onClick={createKey}>
                <Key className="h-4 w-4" /> Create API key
              </Button>
              <div className="divide-y divide-border rounded-lg border border-border">
                {[
                  { name: "Production", scopes: "workflows:read workflows:write", created: "2 days ago", last: "5 min ago" },
                  { name: "CI / deploy", scopes: "workflows:write executions:read", created: "3 weeks ago", last: "1 hour ago" },
                ].map((k) => (
                  <div key={k.name} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{k.name}</p>
                      <p className="truncate font-mono text-[11px] text-muted-foreground">{k.scopes}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">last used {k.last}</span>
                    <Badge variant="secondary">{k.created}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Notification preferences</CardTitle>
              <CardDescription>Choose how you hear about workflow activity.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { label: "Workflow failures", desc: "Alert me immediately when a workflow fails after retries" },
                { label: "Daily digest", desc: "Summary of runs, failures, and cost every morning" },
                { label: "Connector health", desc: "Notify when a connector degrades or goes down" },
                { label: "Weekly product updates", desc: "New connectors, features, and improvements" },
              ].map((n) => (
                <div key={n.label} className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium">{n.label}</p>
                    <p className="text-xs text-muted-foreground">{n.desc}</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Workspace preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">Reduce motion</p>
                  <p className="text-xs text-muted-foreground">Minimize animations across the product</p>
                </div>
                <Switch />
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">Default to light theme</p>
                  <p className="text-xs text-muted-foreground">Override the system preference</p>
                </div>
                <Switch />
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">Confirm before destructive actions</p>
                  <p className="text-xs text-muted-foreground">Require confirmation for deletes and pauses</p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
