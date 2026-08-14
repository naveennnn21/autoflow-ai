"use client";

import { api, streamSse, type SseFrame } from "./client";
import type { PlannerChatResponse, PlannerHealth } from "@/types";

export interface PlannerPlanResponse {
  plan: Record<string, unknown> | null;
  runtime_definition: Record<string, unknown> | null;
  intent: string;
  intent_confidence: number;
  entities: Record<string, unknown>;
  reasoning: unknown[];
  provider: string;
  model: string;
  token_usage: Record<string, number>;
  latency_ms: number;
  warnings: string[];
  errors: string[];
}

export interface PlannerCompileResponse {
  ok: boolean;
  intent?: string;
  clarification_required?: boolean;
  clarification_questions?: string[];
  errors?: string[];
  reply?: string;
  clarifications?: string[];
  preview?: {
    name: string;
    description: string;
    steps: { connector: string; action: string; label: string }[];
    estimate: string;
  } | null;
  spec?: Record<string, unknown> | null;
  plan?: Record<string, unknown> | null;
  diagnostics?: {
    errors?: string[];
    warnings?: string[];
    node_count?: number;
    edge_count?: number;
    undefined_variables?: string[];
    stage_times_ms?: Record<string, number>;
    total_ms?: number;
  };
  metrics?: {
    confidence?: number;
    estimated_cost?: number;
    estimated_latency_ms?: number;
    provider?: string;
    model?: string;
    latency_ms?: number;
  };
}

export interface PlannerStreamHandlers {
  onStage?: (stage: string, label: string) => void;
  onToken?: (text: string) => void;
  onMeta?: (meta: PlannerCompileResponse) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

export const plannerApi = {
  chat: (message: string, conversationId = "") =>
    api.post<PlannerChatResponse>("/planner/chat", {
      message,
      conversation_id: conversationId,
    }),

  compile: (prompt: string, conversationId = "") =>
    api.post<PlannerCompileResponse>("/planner/compile", {
      prompt,
      conversation_id: conversationId,
    }),

  streamChat: (message: string, handlers: PlannerStreamHandlers, conversationId = "") =>
    streamSse("/planner/chat/stream", {
      method: "POST",
      body: { message, conversation_id: conversationId },
      onFrame: (frame: SseFrame) => {
        switch (frame.event) {
          case "stage":
            handlers.onStage?.(String(frame.data.stage ?? ""), String(frame.data.label ?? ""));
            break;
          case "token":
            handlers.onToken?.(String(frame.data.text ?? ""));
            break;
          case "meta":
            handlers.onMeta?.(frame.data as unknown as PlannerCompileResponse);
            break;
          case "error":
            handlers.onError?.(new Error(String(frame.data.message ?? "Planner error")));
            break;
          case "done":
            handlers.onDone?.();
            break;
          default:
            break;
        }
      },
      onError: (err) => handlers.onError?.(err),
      onClose: () => handlers.onDone?.(),
    }),

  plan: (prompt: string) =>
    api.post<PlannerPlanResponse>("/planner/plan", { prompt }),

  health: () => api.get<PlannerHealth>("/planner/health"),
};
