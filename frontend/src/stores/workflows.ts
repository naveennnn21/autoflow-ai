"use client";

import { create } from "zustand";
import type { Workflow } from "@/types";
import { workflows as seed } from "@/lib/mock-workflows";

interface WorkflowState {
  workflows: Workflow[];
  search: string;
  setSearch: (q: string) => void;
  toggleFavorite: (id: string) => void;
  setStatus: (id: string, status: Workflow["status"]) => void;
  addWorkflow: (wf: Workflow) => void;
  removeWorkflow: (id: string) => void;
}

export const useWorkflows = create<WorkflowState>((set) => ({
  workflows: seed,
  search: "",
  setSearch: (search) => set({ search }),
  toggleFavorite: (id) =>
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? { ...w, favorite: !w.favorite } : w)),
    })),
  setStatus: (id, status) =>
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? { ...w, status } : w)),
    })),
  addWorkflow: (workflow) => set((s) => ({ workflows: [workflow, ...s.workflows] })),
  removeWorkflow: (id) =>
    set((s) => ({ workflows: s.workflows.filter((w) => w.id !== id) })),
}));
