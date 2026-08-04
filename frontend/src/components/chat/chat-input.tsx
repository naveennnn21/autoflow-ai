"use client";

import * as React from "react";
import { ArrowUp } from "lucide-react";
import { useChat } from "@/stores/chat";
import { Button } from "@/components/ui/button";

const suggestions = [
  "Monitor competitors and notify Slack",
  "Process invoices from Gmail",
  "Automate GitHub release notes",
  "Generate weekly analytics reports",
  "Sync customer data to Airtable",
];

export function ChatInput() {
  const send = useChat((s) => s.send);
  const isStreaming = useChat((s) => s.isStreaming);
  const [value, setValue] = React.useState("");

  const submit = (text: string) => {
    const t = text.trim();
    if (!t || isStreaming) return;
    setValue("");
    send(t);
  };

  return (
    <div className="space-y-3">
      {/* Large composer */}
      <div className="relative rounded-2xl border border-border/60 bg-card/80 p-1.5 transition-all focus-within:border-primary/50 focus-within:shadow-[0_0_32px_-8px_hsl(var(--primary)/0.35)]">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(value);
            }
          }}
          rows={1}
          placeholder="What do you want to automate?"
          className="max-h-32 w-full resize-none bg-transparent px-4 py-3 text-sm outline-none placeholder:text-muted-foreground/60"
          style={{ minHeight: "48px" }}
        />
        <div className="flex items-center justify-between px-3 pb-1 pt-0">
          <span className="text-[11px] text-muted-foreground/50">Enter to send · Shift+Enter for new line</span>
          <Button
            size="icon"
            onClick={() => submit(value)}
            disabled={!value.trim() || isStreaming}
            aria-label="Send"
            className="h-9 w-9 rounded-xl bg-primary text-primary-foreground shadow-[0_4px_16px_-4px_hsl(var(--primary)/0.6)] transition-all hover:brightness-110 active:scale-95 disabled:opacity-40"
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => submit(s)}
            disabled={isStreaming}
            className="rounded-full border border-border/60 bg-card/50 px-3 py-1.5 text-xs text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-foreground hover:shadow-[0_4px_16px_-6px_hsl(var(--primary)/0.4)] disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}