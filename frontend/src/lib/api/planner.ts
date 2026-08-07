"use client";

import { api } from "./client";
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

export const plannerApi = {
  chat: (message: string, conversationId = "") =>
    api.post<PlannerChatResponse>("/planner/chat", {
      message,
      conversation_id: conversationId,
    }),

  plan: (prompt: string) =>
    api.post<PlannerPlanResponse>("/planner/plan", { prompt }),

  health: () => api.get<PlannerHealth>("/planner/health"),
};
