"use client";

import { useEffect, useMemo } from "react";
import { Plus, RefreshCw, Search, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { WorkflowCard } from "@/components/dashboard/workflow-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CardSkeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useWorkflows } from "@/stores/workflows";
import { useDebounce } from "@/hooks/use-debounce";
import Link from "next/link";

export default function WorkflowsPage() {
  const { workflows, loading, error, loaded, hasMore, search, setSearch, load, loadMore } = useWorkflows();
  const debounced = useDebounce(search, 200);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = debounced.toLowerCase();
    if (!q) return workflows;
    return workflows.filter(
      (w) =>
        w.name.toLowerCase().includes(q) ||
        w.description.toLowerCase().includes(q) ||
        w.tags?.some((t) => t.toLowerCase().includes(q)),
    );
  }, [workflows, debounced]);

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader title="Workflows" description={`${loaded ? workflows.length : "—"} automations loaded in your workspace.`}>
        <Button variant="gradient" asChild>
          <Link href="/chat">
            <Plus className="h-4 w-4" />
            Create with AI
          </Link>
        </Button>
      </PageHeader>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search workflows..."
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && !loading ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-12 text-center">
          <p className="font-medium">Couldn&apos;t load workflows</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" className="mt-4 gap-2" onClick={() => void load({ reset: true })}>
            <RefreshCw className="h-4 w-4" /> Retry
          </Button>
        </div>
      ) : loading && !loaded ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        loaded ? (
          <EmptyState
            icon={<Sparkles className="h-6 w-6" />}
            title={search ? "No workflows match your search" : "No workflows yet"}
            description={
              search
                ? "Try a different search term."
                : "Describe the automation you want and the AI copilot will build it for you."
            }
            action={
              !search ? (
                <Button asChild size="sm" className="gap-1.5">
                  <Link href="/chat">
                    <Sparkles className="h-3.5 w-3.5" /> Create with AI
                  </Link>
                </Button>
              ) : undefined
            }
          />
        ) : null
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((wf) => (
            <WorkflowCard key={wf.id} workflow={wf} />
          ))}
        </div>
      )}

      {hasMore && filtered.length === workflows.length && (
        <div className="flex justify-center pt-2">
          <Button variant="outline" size="sm" onClick={() => void loadMore()} disabled={loading}>
            {loading ? "Loading..." : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
