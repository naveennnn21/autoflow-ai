"use client";

import { api, withQuery } from "./client";
import type { AnalyticsDashboard } from "@/types";

export type AnalyticsPeriod = "7d" | "30d" | "90d";

export const analyticsApi = {
  dashboard: (period: AnalyticsPeriod = "30d") =>
    api.get<AnalyticsDashboard>(withQuery("/analytics/dashboard", { period })),
};
