"use client";

import { api, withQuery } from "./client";
import { mapWorkflow, toBackendConfig } from "./mappers";
import type { Paginated, Workflow } from "@/types";

export interface WorkflowListParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface WorkflowPayload {
  organization_id?: string;
  name: string;
  description?: string;
  status?: string;
  config?: Record<string, unknown>;
}

export const workflowsApi = {
  async list(params: WorkflowListParams = {}): Promise<Paginated<Workflow>> {
    const res = await api.get<Paginated<Record<string, unknown>>>(
      withQuery("/workflow", params),
    );
    return {
      ...res,
      items: (res.items ?? []).map((raw) => mapWorkflow(raw as never)),
    };
  },

  async get(id: string): Promise<Workflow> {
    const raw = await api.get<Record<string, unknown>>(`/workflow/${id}`);
    return mapWorkflow(raw as never);
  },

  async create(payload: WorkflowPayload): Promise<Workflow> {
    const raw = await api.post<Record<string, unknown>>("/workflow", payload);
    return mapWorkflow(raw as never);
  },

  async update(id: string, payload: Partial<WorkflowPayload>): Promise<Workflow> {
    const raw = await api.patch<Record<string, unknown>>(`/workflow/${id}`, payload);
    return mapWorkflow(raw as never);
  },

  async remove(id: string): Promise<void> {
    await api.delete(`/workflow/${id}`);
  },

  async setFavorite(id: string, wf: Workflow, favorite: boolean): Promise<Workflow> {
    return workflowsApi.update(id, {
      config: { ...toBackendConfig(wf), favorite },
    });
  },

  count: () => api.get<{ count: number }>("/workflow/count"),
};
