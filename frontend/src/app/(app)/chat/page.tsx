"use client";

import * as React from "react";
import { useChat } from "@/stores/chat";
import { Message } from "@/components/chat/message";
import { ChatInput } from "@/components/chat/chat-input";
import { Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function ChatPage() {
  const messages = useChat((s) => s.messages);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-5xl flex-col">
      {/* Minimal header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">AI Copilot</h1>
          <p className="text-xs text-muted-foreground">Describe your automation in plain English</p>
        </div>
        <Badge variant="gradient" className="gap-1.5 text-[11px]">
          <Sparkles className="h-3 w-3" />
          Planner v1
        </Badge>
      </div>

      {/* Messages area */}
      <div className="flex-1 space-y-6 overflow-y-auto py-6 no-scrollbar">
        {messages.length === 1 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Sparkles className="h-8 w-8 text-primary" />
            </div>
            <p className="text-xl font-medium tracking-tight">What do you want to automate?</p>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              Describe your workflow in natural language. I&apos;ll design, validate, and deploy it for you.
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <Message key={m.id} message={m} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="border-t border-border/40 pt-4 pb-2">
        <ChatInput />
      </div>
    </div>
  );
}