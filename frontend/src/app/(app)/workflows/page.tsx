"use client";

import { useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { WorkflowCard } from "@/components/dashboard/workflow-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkflows } from "@/stores/workflows";
import { useDebounce } from "@/hooks/use-debounce";
import Link from "next/link";

export default function WorkflowsPage() {
  const workflows = useWorkflows((s) => s.workflows);
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search, 200);

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
      <PageHeader title="Workflows" description={`${workflows.length} automations in your workspace.`}>
        <Button variant="gradient" asChild>
          <Link href="/chat">
            <Plus className="h-4 w-4" />
            Create with AI
          </Link>
        </Button>
      </PageHeader>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search workflows..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-16 text-center text-sm text-muted-foreground">
          No workflows match your search.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((wf) => (
            <WorkflowCard key={wf.id} workflow={wf} />
          ))}
        </div>
      )}
    </div>
  );
}
