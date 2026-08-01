"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SessionUser } from "@/types";
import { data } from "@/services/data";

interface SessionState {
  user: SessionUser | null;
  loading: boolean;
  login: (email: string) => Promise<void>;
  logout: () => void;
  hydrate: () => Promise<void>;
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      user: null,
      loading: true,
      login: async (email) => {
        const user = await data.login(email);
        set({ user, loading: false });
      },
      logout: () => set({ user: null }),
      hydrate: async () => {
        try {
          const user = await data.me();
          set({ user, loading: false });
        } catch {
          set({ loading: false });
        }
      },
    }),
    { name: "af-session", partialize: (s) => ({ user: s.user }) },
  ),
);
