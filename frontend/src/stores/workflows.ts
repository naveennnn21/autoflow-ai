"use client";

import { create } from "zustand";
import { workflowsApi } from "@/lib/api/workflows";
import type { Workflow } from "@/types";

const PAGE_SIZE = 24;

interface WorkflowState {
  workflows: Workflow[];
  loading: boolean;
  error: string | null;
  loaded: boolean;
  page: number;
  total: number;
  hasMore: boolean;
  search: string;
  setSearch: (q: string) => void;
  load: (opts?: { reset?: boolean }) => Promise<void>;
  loadMore: () => Promise<void>;
  toggleFavorite: (id: string) => Promise<void>;
  setStatus: (id: string, status: Workflow["status"]) => Promise<void>;
  addWorkflow: (wf: Workflow) => void;
  removeWorkflow: (id: string) => Promise<void>;
}

export const useWorkflows = create<WorkflowState>((set, get) => ({
  workflows: [],
  loading: false,
  error: null,
  loaded: false,
  page: 0,
  total: 0,
  hasMore: false,
  search: "",

  setSearch: (search) => set({ search }),

  load: async ({ reset = false } = {}) => {
    if (get().loading) return;
    if (get().loaded && !reset) return;
    set({ loading: true, error: null });
    try {
      const res = await workflowsApi.list({ page: 1, page_size: PAGE_SIZE });
      set({
        workflows: res.items ?? [],
        total: res.total ?? (res.items ?? []).length,
        page: 1,
        hasMore: (res.total_pages ?? 1) > 1,
        loading: false,
        loaded: true,
        error: null,
      });
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : "Failed to load workflows" });
    }
  },

  loadMore: async () => {
    const { page, total, loading, workflows } = get();
    if (loading || workflows.length >= total) return;
    set({ loading: true });
    try {
      const res = await workflowsApi.list({ page: page + 1, page_size: PAGE_SIZE });
      const merged = [...workflows, ...(res.items ?? [])];
      set({
        workflows: merged,
        page: page + 1,
        hasMore: (res.total_pages ?? 1) > page + 1,
        loading: false,
      });
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : "Failed to load more workflows" });
    }
  },

  toggleFavorite: async (id) => {
    const wf = get().workflows.find((w) => w.id === id);
    if (!wf) return;
    const next = !wf.favorite;
    // optimistic
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? { ...w, favorite: next } : w)),
    }));
    try {
      const updated = await workflowsApi.setFavorite(id, wf, next);
      set((s) => ({
        workflows: s.workflows.map((w) => (w.id === id ? { ...updated, favorite: next } : w)),
      }));
    } catch {
      // revert
      set((s) => ({
        workflows: s.workflows.map((w) => (w.id === id ? { ...w, favorite: wf.favorite } : w)),
      }));
      throw new Error("Could not update favorite");
    }
  },

  setStatus: async (id, status) => {
    const wf = get().workflows.find((w) => w.id === id);
    if (!wf) return;
    const prev = wf.status;
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? { ...w, status } : w)),
    }));
    try {
      const updated = await workflowsApi.update(id, { status });
      set((s) => ({
        workflows: s.workflows.map((w) => (w.id === id ? { ...updated, status } : w)),
      }));
    } catch {
      set((s) => ({
        workflows: s.workflows.map((w) => (w.id === id ? { ...w, status: prev } : w)),
      }));
      throw new Error("Could not update workflow status");
    }
  },

  addWorkflow: (workflow) =>
    set((s) => ({ workflows: [workflow, ...s.workflows], total: s.total + 1 })),

  removeWorkflow: async (id) => {
    const wf = get().workflows.find((w) => w.id === id);
    set((s) => ({
      workflows: s.workflows.filter((w) => w.id !== id),
      total: Math.max(0, s.total - 1),
    }));
    try {
      await workflowsApi.remove(id);
    } catch {
      if (wf) {
        set((s) => ({ workflows: [...s.workflows, wf] }));
      }
      throw new Error("Could not delete workflow");
    }
  },
}));
