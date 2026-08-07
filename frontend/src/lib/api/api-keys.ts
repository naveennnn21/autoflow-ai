"use client";

import { api, withQuery } from "./client";
import type { ApiKey, Paginated } from "@/types";

export interface CreateApiKeyPayload {
  organization_id: string;
  user_id: string;
  name: string;
  key_prefix: string;
  scopes?: Record<string, unknown>;
}

export const apiKeysApi = {
  list: (params: { page?: number; page_size?: number } = {}) =>
    api.get<Paginated<ApiKey>>(withQuery("/api_key", params)),

  create: (payload: CreateApiKeyPayload) =>
    api.post<ApiKey>("/api_key", payload),

  update: (id: string, payload: Partial<CreateApiKeyPayload>) =>
    api.patch<ApiKey>(`/api_key/${id}`, payload),

  remove: (id: string) => api.delete(`/api_key/${id}`),
};
