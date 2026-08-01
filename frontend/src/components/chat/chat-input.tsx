"use client";

import * as React from "react";
import { ArrowUp, Paperclip } from "lucide-react";
import { useChat } from "@/stores/chat";
import { Button } from "@/components/ui/button";

const suggestions = [
  "When a new contact is created in HubSpot, enrich it with GitHub and log to Airtable",
  "Send a weekly revenue summary from Stripe to email every Monday",
  "When a Slack message mentions 'urgent', create a Linear issue and notify the team",
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
      <div className="relative rounded-2xl border border-border/80 bg-card/90 p-2 shadow-[0_8px_32px_-16px_rgba(0,0,0,0.5)] backdrop-blur-xl transition-all focus-within:border-primary/50 focus-within:shadow-[0_0_32px_-8px_hsl(var(--primary)/0.45)]">
        <div aria-hidden className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(value);
            }
          }}
          rows={2}
          placeholder="Describe the automation you want to build..."
          className="max-h-40 w-full resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
        />
        <div className="flex items-center justify-between px-1 pb-0.5">
          <Button variant="ghost" size="icon-sm" aria-label="Attach file" className="text-muted-foreground">
            <Paperclip className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            onClick={() => submit(value)}
            disabled={!value.trim() || isStreaming}
            aria-label="Send"
            className="bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-[0_4px_16px_-4px_hsl(var(--primary)/0.6)] transition-transform hover:scale-105 active:scale-95"
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => submit(s)}
            className="rounded-full border border-border/70 bg-card/60 px-3 py-1.5 text-left text-xs text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-foreground hover:shadow-[0_4px_16px_-6px_hsl(var(--primary)/0.4)]"
          >
            {s.length > 72 ? `${s.slice(0, 72)}…` : s}
          </button>
        ))}
      </div>
    </div>
  );
}
