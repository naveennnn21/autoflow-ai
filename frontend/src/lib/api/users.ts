"use client";

import { api, withQuery } from "./client";
import type { Paginated, SessionUser } from "@/types";
import { mapBackendUser } from "./mappers";

export interface UserPayload {
  full_name?: string;
  avatar_url?: string;
  is_verified?: boolean;
}

export const usersApi = {
  async list(params: { page?: number; page_size?: number; search?: string } = {}): Promise<Paginated<SessionUser>> {
    const res = await api.get<Paginated<Record<string, unknown>>>(withQuery("/user", params));
    return {
      ...res,
      items: (res.items ?? []).map((raw) => mapBackendUser(raw as never)),
    };
  },

  get: (id: string) => api.get<Record<string, unknown>>(`/user/${id}`),

  update: (id: string, payload: UserPayload) =>
    api.patch<Record<string, unknown>>(`/user/${id}`, payload),
};
