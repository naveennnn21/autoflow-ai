"use client";

import { create } from "zustand";
import { toast } from "sonner";
import { plannerApi } from "@/lib/api/planner";
import type { ChatMessage, WorkflowPreview } from "@/types";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  send: (text: string) => Promise<void>;
  clear: () => void;
}

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm your automation copilot. Describe what you want to automate and I'll design, validate, and deploy the workflow for you.\n\nTry something like:\n- \"When a new contact is created in HubSpot, enrich it with GitHub and log it to Airtable\"\n- \"Send a weekly revenue summary from Stripe to my email every Monday\"",
  timestamp: new Date().toISOString(),
};

export const useChat = create<ChatState>((set, get) => ({
  messages: [WELCOME],
  isStreaming: false,

  send: async (text) => {
    const trimmed = text.trim();
    if (!trimmed || get().isStreaming) return;
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isStreaming: true }));

    const assistantId = `a_${Date.now()}`;
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString(),
          thinking: true,
          streaming: true,
        },
      ],
    }));

    try {
      // Keep the planning indicator visible while the real planner runs.
      const [res] = await Promise.all([
        plannerApi.chat(trimmed),
        new Promise((r) => setTimeout(r, 600)),
      ]);

      const preview: WorkflowPreview | undefined = res.preview
        ? {
            name: res.preview.name,
            description: res.preview.description,
            steps: res.preview.steps ?? [],
            estimate: res.preview.estimate,
          }
        : undefined;

      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                thinking: false,
                content: res.reply || "I couldn't produce a plan for that. Please rephrase and try again.",
                clarifications: res.clarifications ?? [],
                workflowPreview: preview,
                streaming: false,
              }
            : m,
        ),
        isStreaming: false,
      }));
    } catch (err) {
      const detail = err instanceof Error ? err.message : "The planner is unreachable right now.";
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                thinking: false,
                streaming: false,
                content: `I hit an error while planning this workflow:\n\n> ${detail}\n\nMake sure the API is running and try again.`,
              }
            : m,
        ),
        isStreaming: false,
      }));
      toast.error("Planner request failed", { description: detail });
    }
  },

  clear: () => set({ messages: [WELCOME] }),
}));
