"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Check, RefreshCw, TriangleAlert, User } from "lucide-react";
import { TypingDots } from "@/components/motion/typing";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useChat } from "@/stores/chat";
import { ClarificationCard } from "./clarification";
import { WorkflowPreviewCard } from "./workflow-preview";
import type { ChatMessage as ChatMessageType, PlanMetrics } from "@/types";

function stageIndex(stage: string): number {
  const order = ["intent", "planning", "compiling", "estimating", "clarify"];
  const idx = order.indexOf(stage);
  return idx === -1 ? 0 : idx;
}

function MetricsRow({ metrics }: { metrics: PlanMetrics }) {
  const items: { label: string; value: string }[] = [];
  if (typeof metrics.confidence === "number") {
    items.push({ label: "Confidence", value: `${Math.round(metrics.confidence * 100)}%` });
  }
  if (typeof metrics.estimatedCost === "number") {
    items.push({ label: "Est. cost/run", value: `$${metrics.estimatedCost.toFixed(4)}` });
  }
  if (typeof metrics.estimatedLatencyMs === "number") {
    items.push({ label: "Est. latency", value: `~${(metrics.estimatedLatencyMs / 1000).toFixed(1)}s` });
  }
  if (typeof metrics.nodeCount === "number") {
    items.push({ label: "Nodes", value: String(metrics.nodeCount) });
  }
  if (typeof metrics.edgeCount === "number") {
    items.push({ label: "Edges", value: String(metrics.edgeCount) });
  }
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {items.map((it) => (
        <div
          key={it.label}
          className="flex items-center gap-1.5 rounded-lg border border-border/60 bg-background/50 px-2.5 py-1.5"
        >
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{it.label}</span>
          <span className="text-xs font-semibold text-foreground">{it.value}</span>
        </div>
      ))}
    </div>
  );
}

export function Message({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";
  const retry = useChat((s) => s.retry);
  const currentStage = message.activeStage ?? "";
  const stageIdx = stageIndex(currentStage);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 26 }}
      className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}
    >
      {!isUser && (
        <Avatar className="mt-0.5 h-8 w-8 ring-1 ring-primary/30">
          <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-[0_0_16px_-4px_hsl(var(--primary)/0.6)]">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}

      <div className={cn("max-w-[85%] space-y-3 sm:max-w-[75%]", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-[inset_0_1px_0_0_hsl(var(--foreground)/0.04)]",
            isUser
              ? "rounded-br-sm border-transparent bg-gradient-to-br from-primary to-secondary/90 text-primary-foreground shadow-[0_8px_24px_-8px_hsl(var(--primary)/0.5)]"
              : "rounded-bl-sm border-border/70 bg-card/90 backdrop-blur-xl",
          )}
        >
          {message.thinking && message.stages ? (
            <div className="space-y-3 py-1">
              <div className="flex items-center gap-2.5 text-muted-foreground">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
                </span>
                <span className="text-xs font-medium">Planning your workflow</span>
                <TypingDots />
              </div>
              <div className="space-y-1.5">
                {message.stages.map((st, i) => {
                  const state =
                    i < stageIdx || currentStage === "clarify"
                      ? "done"
                      : i === stageIdx
                        ? "active"
                        : "todo";
                  return (
                    <div key={st.stage} className="flex items-center gap-2">
                      {state === "done" ? (
                        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success/15">
                          <Check className="h-2.5 w-2.5 text-success" />
                        </span>
                      ) : state === "active" ? (
                        <span className="relative flex h-4 w-4 items-center justify-center">
                          <span className="absolute h-4 w-4 animate-ping rounded-full bg-primary/30" />
                          <span className="relative h-2 w-2 rounded-full bg-primary" />
                        </span>
                      ) : (
                        <span className="h-4 w-4 rounded-full border border-border" />
                      )}
                      <span
                        className={cn(
                          "text-xs",
                          state === "active" ? "font-medium text-foreground" : "text-muted-foreground",
                        )}
                      >
                        {st.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : message.thinking ? (
            <div className="flex items-center gap-2.5 text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
              </span>
              <span className="text-xs font-medium">Planning your workflow</span>
              <TypingDots />
            </div>
          ) : message.content ? (
            <div className="prose prose-sm prose-invert max-w-none prose-p:my-2 prose-strong:text-foreground">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          ) : null}
        </div>

        {message.error && !message.content && (
          <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
            {message.error}
            <Button
              variant="ghost"
              size="icon-sm"
              className="ml-1 h-6 w-6"
              aria-label="Retry generation"
              onClick={() => void retry(message.id)}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {message.planMetrics && <MetricsRow metrics={message.planMetrics} />}

        {message.clarifications && message.clarifications.length > 0 && (
          <div className="space-y-2">
            <Badge variant="secondary" className="text-[11px]">Refine your automation</Badge>
            <div className="flex flex-wrap gap-2">
              {message.clarifications.map((q) => (
                <ClarificationCard key={q} question={q} />
              ))}
            </div>
          </div>
        )}

        {message.workflowPreview && (
          <WorkflowPreviewCard preview={message.workflowPreview} />
        )}
      </div>

      {isUser && (
        <Avatar className="mt-0.5 h-8 w-8">
          <AvatarFallback className="bg-muted text-foreground">
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
    </motion.div>
  );
}