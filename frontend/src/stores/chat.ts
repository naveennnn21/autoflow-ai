"use client";

import { create } from "zustand";
import { toast } from "sonner";
import { plannerApi } from "@/lib/api/planner";
import type { ChatMessage, ChatStage, PlanMetrics, WorkflowPreview } from "@/types";

const HISTORY_KEY = "af-chat-history";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  conversationId: string;
  /** Abort handler for the in-flight stream (cancel generation). */
  abortStream: (() => void) | null;
  send: (text: string) => Promise<void>;
  retry: (messageId: string) => Promise<void>;
  cancel: () => void;
  clear: () => void;
  history: string[];
}

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm your automation copilot. Describe what you want to automate and I'll design, validate, and deploy the workflow for you.\n\nTry something like:\n- \"When a new contact is created in HubSpot, enrich it with GitHub and log it to Airtable\"\n- \"Send a weekly revenue summary from Stripe to my email every Monday\"",
  timestamp: new Date().toISOString(),
};

function newId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function loadHistory(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? (JSON.parse(raw) as string[]) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 12) : [];
  } catch {
    return [];
  }
}

function saveHistory(items: string[]): void {
  try {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 12)));
  } catch {
    // storage unavailable - history is best-effort
  }
}

const STAGES: ChatStage[] = [
  { stage: "intent", label: "Understanding your request" },
  { stage: "planning", label: "Selecting connectors & steps" },
  { stage: "compiling", label: "Compiling workflow spec" },
  { stage: "estimating", label: "Estimating cost & latency" },
];

export const useChat = create<ChatState>((set, get) => ({
  messages: [WELCOME],
  isStreaming: false,
  conversationId: "",
  abortStream: null,

  send: async (text) => {
    const trimmed = text.trim();
    if (!trimmed || get().isStreaming) return;

    const userMsg: ChatMessage = {
      id: newId("u"),
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    set((s) => {
      const history = [
        trimmed,
        ...s.history.filter((h) => h.toLowerCase() !== trimmed.toLowerCase()),
      ];
      saveHistory(history);
      return { messages: [...s.messages, userMsg], isStreaming: true, history };
    });

    const assistantId = newId("a");
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
          stages: STAGES,
          activeStage: "intent",
        },
      ],
    }));

    const abort = plannerApi.streamChat(
      trimmed,
      {
        onStage: (stage) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === assistantId ? { ...m, activeStage: stage } : m,
            ),
          }));
        },
        onToken: (token) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + token, thinking: false }
                : m,
            ),
          }));
        },
        onMeta: (meta) => {
          const preview: WorkflowPreview | undefined = meta.preview
            ? {
                name: meta.preview.name,
                description: meta.preview.description,
                steps: meta.preview.steps ?? [],
                estimate: meta.preview.estimate,
              }
            : undefined;
          const metrics: PlanMetrics | undefined = meta.metrics
            ? {
                confidence: meta.metrics.confidence,
                estimatedCost: meta.metrics.estimated_cost,
                estimatedLatencyMs: meta.metrics.estimated_latency_ms,
                provider: meta.metrics.provider,
                model: meta.metrics.model,
                latencyMs: meta.metrics.latency_ms,
                nodeCount: meta.diagnostics?.node_count,
                edgeCount: meta.diagnostics?.edge_count,
              }
            : undefined;
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    thinking: false,
                    streaming: false,
                    content:
                      m.content ||
                      meta.reply ||
                      "I couldn't produce a plan for that. Please rephrase and try again.",
                    clarifications:
                      meta.clarifications ?? meta.clarification_questions ?? [],
                    workflowPreview: preview,
                    planMetrics: metrics,
                    error: meta.ok === false && meta.errors?.length
                      ? meta.errors.join("; ")
                      : undefined,
                  }
                : m,
            ),
            isStreaming: false,
          }));
        },
        onError: (err) => {
          const detail =
            err instanceof Error ? err.message : "The planner is unreachable right now.";
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    thinking: false,
                    streaming: false,
                    content:
                      m.content ||
                      `I hit an error while planning this workflow:\n\n> ${detail}\n\nMake sure the API is running and try again.`,
                    error: detail,
                  }
                : m,
            ),
            isStreaming: false,
          }));
          toast.error("Planner request failed", { description: detail });
        },
        onDone: () => {
          set((s) => ({
            isStreaming: false,
            messages: s.messages.map((m) =>
              m.id === assistantId ? { ...m, streaming: false, thinking: false } : m,
            ),
            abortStream: null,
          }));
        },
      },
      get().conversationId,
    );
    set({ abortStream: abort });
  },

  retry: async (messageId) => {
    const state = get();
    if (state.isStreaming) return;
    const target = state.messages.find((m) => m.id === messageId);
    if (!target || target.role !== "assistant") return;
    const lastUser = [...state.messages]
      .reverse()
      .find((m) => m.role === "user" && m.timestamp <= target.timestamp);
    if (!lastUser) return;

    // Replace the failed message with a fresh one and re-plan.
    const freshId = newId("a");
    set((s) => ({
      isStreaming: true,
      messages: s.messages.map((m) =>
        m.id === messageId
          ? {
              id: freshId,
              role: "assistant",
              content: "",
              timestamp: new Date().toISOString(),
              thinking: true,
              streaming: true,
              stages: STAGES,
              activeStage: "intent",
            }
          : m,
      ),
    }));

    const abort = plannerApi.streamChat(
      lastUser.content,
      {
        onStage: (stage) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === freshId ? { ...m, activeStage: stage } : m,
            ),
          }));
        },
        onToken: (token) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === freshId
                ? { ...m, content: m.content + token, thinking: false }
                : m,
            ),
          }));
        },
        onMeta: (meta) => {
          const preview: WorkflowPreview | undefined = meta.preview
            ? {
                name: meta.preview.name,
                description: meta.preview.description,
                steps: meta.preview.steps ?? [],
                estimate: meta.preview.estimate,
              }
            : undefined;
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === freshId
                ? {
                    ...m,
                    thinking: false,
                    streaming: false,
                    content: m.content || meta.reply || "",
                    clarifications: meta.clarifications ?? [],
                    workflowPreview: preview,
                    error: meta.ok === false && meta.errors?.length
                      ? meta.errors.join("; ")
                      : undefined,
                  }
                : m,
            ),
            isStreaming: false,
          }));
        },
        onError: (err) => {
          set((s) => ({
            isStreaming: false,
            messages: s.messages.map((m) =>
              m.id === freshId
                ? {
                    ...m,
                    thinking: false,
                    streaming: false,
                    content:
                      m.content || "The planner is unreachable right now. Try again.",
                    error: err instanceof Error ? err.message : "Planner error",
                  }
                : m,
            ),
          }));
        },
        onDone: () => {
          set((s) => ({
            isStreaming: false,
            messages: s.messages.map((m) =>
              m.id === freshId ? { ...m, streaming: false, thinking: false } : m,
            ),
            abortStream: null,
          }));
        },
      },
      state.conversationId,
    );
    set({ abortStream: abort });
  },

  cancel: () => {
    const abort = get().abortStream;
    if (abort) {
      abort();
      set({ abortStream: null });
    }
    set((s) => ({
      isStreaming: false,
      messages: s.messages.map((m) =>
        m.streaming
          ? { ...m, streaming: false, thinking: false, error: "Generation cancelled" }
          : m,
      ),
    }));
  },

  clear: () => {
    get().abortStream?.();
    set({ messages: [WELCOME], isStreaming: false, abortStream: null, conversationId: "" });
  },

  history: loadHistory(),
}));
