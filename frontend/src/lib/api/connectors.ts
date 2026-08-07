"use client";

import { api, withQuery } from "./client";
import { mapConnector } from "./mappers";
import type { Connector, Paginated } from "@/types";

export interface ConnectorListParams {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const connectorsApi = {
  async list(params: ConnectorListParams = {}): Promise<Paginated<Connector>> {
    const res = await api.get<Paginated<Record<string, unknown>>>(
      withQuery("/connectors", params),
    );
    return {
      ...res,
      items: (res.items ?? []).map((raw) => mapConnector(raw)),
    };
  },

  async get(slug: string): Promise<Connector> {
    const raw = await api.get<Record<string, unknown>>(`/connectors/${encodeURIComponent(slug)}`);
    return mapConnector(raw);
  },
};
