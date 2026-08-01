"use client";

import { MOCK, api } from "./api";
import { connectors as mockConnectors } from "@/lib/mock-connectors";
import { workflows as mockWorkflows } from "@/lib/mock-workflows";
import { executions as mockExecutions, metrics as mockMetrics, activity as mockActivity } from "@/lib/mock-analytics";
import type { ActivityItem, Connector, Execution, Metric, SessionUser, Workflow } from "@/types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

const demoUser: SessionUser = {
  id: "usr_1",
  name: "Ava Torres",
  email: "ava@acme.com",
  role: "admin",
  org: "Acme Corp",
};

export const data = {
  async getConnectors(): Promise<Connector[]> {
    if (MOCK) {
      await delay(240);
      return mockConnectors;
    }
    return api.get<Connector[]>("/marketplace/items");
  },
  async getWorkflows(): Promise<Workflow[]> {
    if (MOCK) {
      await delay(320);
      return mockWorkflows;
    }
    return api.get<Workflow[]>("/workflows");
  },
  async getExecutions(): Promise<Execution[]> {
    if (MOCK) {
      await delay(280);
      return mockExecutions;
    }
    return api.get<Execution[]>("/executions");
  },
  async getMetrics(): Promise<Metric[]> {
    if (MOCK) {
      await delay(200);
      return mockMetrics;
    }
    return api.get<Metric[]>("/monitoring/metrics");
  },
  async getActivity(): Promise<ActivityItem[]> {
    if (MOCK) {
      await delay(220);
      return mockActivity;
    }
    return api.get<ActivityItem[]>("/audit/logs");
  },
  async login(email: string): Promise<SessionUser> {
    if (MOCK) {
      await delay(700);
      return { ...demoUser, email };
    }
    return api.post<SessionUser>("/auth/login", { email });
  },
  async me(): Promise<SessionUser> {
    if (MOCK) {
      await delay(120);
      return demoUser;
    }
    return api.get<SessionUser>("/auth/me");
  },
};
