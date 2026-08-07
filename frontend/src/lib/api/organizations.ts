"use client";

import { api, withQuery } from "./client";
import type { Organization, Paginated } from "@/types";

export interface OrganizationPayload {
  name?: string;
  slug?: string;
  description?: string;
  logo_url?: string;
  tier?: string;
  settings?: Record<string, unknown>;
}

export const organizationsApi = {
  list: (params: { page?: number; page_size?: number; search?: string } = {}) =>
    api.get<Paginated<Organization>>(withQuery("/organization", params)),

  get: (id: string) => api.get<Organization>(`/organization/${id}`),

  update: (id: string, payload: OrganizationPayload) =>
    api.patch<Organization>(`/organization/${id}`, payload),
};
