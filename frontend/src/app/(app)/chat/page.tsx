"use client";

import * as React from "react";
import { useChat } from "@/stores/chat";
import { Message } from "@/components/chat/message";
import { ChatInput } from "@/components/chat/chat-input";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Sparkles } from "lucide-react";

export default function ChatPage() {
  const messages = useChat((s) => s.messages);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <PageHeader
        title="AI Copilot"
        description="Describe your automation in plain English — I'll design, validate, and deploy it."
      >
        <Badge variant="gradient">
          <Sparkles className="h-3 w-3" />
          Planner v1
        </Badge>
      </PageHeader>

      <div className="flex-1 space-y-6 overflow-y-auto py-6 no-scrollbar">
        {messages.map((m) => (
          <Message key={m.id} message={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="pb-2">
        <ChatInput />
      </div>
    </div>
  );
}
