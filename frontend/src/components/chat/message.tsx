"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import { TypingDots } from "@/components/motion/typing";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ClarificationCard } from "./clarification";
import { WorkflowPreviewCard } from "./workflow-preview";
import type { ChatMessage as ChatMessageType } from "@/types";

export function Message({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";

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
          {message.thinking ? (
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
