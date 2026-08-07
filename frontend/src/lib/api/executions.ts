"use client";

import { api, withQuery } from "./client";
import { mapExecution } from "./mappers";
import { workflowsApi } from "./workflows";
import type { BackendExecution, Execution, Paginated } from "@/types";

export interface ExecutionListParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const executionsApi = {
  async list(params: ExecutionListParams = {}): Promise<Paginated<Execution>> {
    const [res, wfs] = await Promise.all([
      api.get<Paginated<BackendExecution>>(withQuery("/execution", params)),
      workflowsApi.list({ page: 1, page_size: 100 }).catch(() => ({ items: [] as never[] }) as Paginated<never>),
    ]);
    const names: Record<string, string> = {};
    for (const wf of wfs.items ?? []) {
      names[wf.id] = wf.name;
    }
    return {
      ...res,
      items: (res.items ?? []).map((raw) => mapExecution(raw, names)),
    };
  },

  get: (id: string) => api.get<BackendExecution>(`/execution/${id}`),

  count: () => api.get<{ count: number }>("/execution/count"),
};
