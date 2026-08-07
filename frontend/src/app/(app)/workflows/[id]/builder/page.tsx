"use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { ArrowLeft, Play, RefreshCw, Save, Settings2, Sparkles, Undo2, Redo2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { FlowCanvas, type FlowCanvasHandle } from "@/components/builder/flow-canvas";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import { workflowsApi } from "@/lib/api/workflows";
import { timeAgo } from "@/lib/utils";

export default function BuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = React.useState<string | null>(null);
  const canvasRef = React.useRef<FlowCanvasHandle>(null);

  React.useEffect(() => {
    void params.then((p) => setId(p.id));
  }, [params]);

  const { data: workflow, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.workflow(id ?? ""),
    queryFn: () => workflowsApi.get(id ?? ""),
    enabled: !!id,
  });

  if (!id || isLoading) {
    return (
      <div className="flex h-[calc(100vh-6.5rem)] flex-col">
        <div className="flex items-center gap-3 pb-4">
          <Skeleton className="h-9 w-9" />
          <div className="space-y-1.5">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-3 w-40" />
          </div>
        </div>
        <Skeleton className="min-h-0 flex-1" />
      </div>
    );
  }

  if (isError || !workflow) {
    if (!isError) notFound();
    return (
      <div className="flex h-[calc(100vh-6.5rem)] flex-col items-center justify-center">
        <EmptyState
          title="Couldn't load this workflow"
          description="The workflow API is unreachable or the workflow was deleted."
          action={
            <Button variant="outline" size="sm" className="gap-2" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col">
      <div className="flex flex-wrap items-center gap-3 pb-4">
        <Button variant="ghost" size="icon-sm" asChild aria-label="Back to workflows">
          <Link href="/workflows">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-lg font-semibold tracking-tight">{workflow.name}</h1>
            <Badge variant={workflow.status === "active" ? "success" : "secondary"}>{workflow.status}</Badge>
          </div>
          <p className="truncate text-xs text-muted-foreground">
            {workflow.nodes.length} nodes · {workflow.edges.length} edges · updated {timeAgo(workflow.updatedAt)}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button variant="ghost" size="icon-sm" aria-label="Undo"><Undo2 className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon-sm" aria-label="Redo"><Redo2 className="h-4 w-4" /></Button>
          <Button variant="outline" size="sm"><Save className="h-4 w-4" /> Save draft</Button>
          <Button variant="outline" size="icon-sm" aria-label="Settings"><Settings2 className="h-4 w-4" /></Button>
          <Button size="sm" className="gap-1.5">
            <Sparkles className="h-4 w-4" />
            Improve with AI
          </Button>
          <Button variant="secondary" size="sm" onClick={() => canvasRef.current?.run()}><Play className="h-4 w-4" /> Test run</Button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <FlowCanvas key={workflow.id} ref={canvasRef} workflow={workflow} />
      </div>
    </div>
  );
}
