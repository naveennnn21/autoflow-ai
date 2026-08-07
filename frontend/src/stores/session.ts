"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "@/lib/api/auth";
import {
  UNAUTHORIZED_EVENT,
  clearAuth,
  setAccessToken,
  setOrgId,
  setRefreshToken,
} from "@/lib/api/client";
import { mapSessionUser } from "@/lib/api/mappers";
import type { AuthResponse, SessionUser } from "@/types";

interface SessionState {
  user: SessionUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  orgId: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

function applyAuth(state: Partial<SessionState>, res: AuthResponse) {
  const org = res.org ?? null;
  setAccessToken(res.access_token ?? null);
  setRefreshToken(res.refresh_token ?? null);
  setOrgId(org?.id ?? null);
  const user = mapSessionUser({
    ...(res.user ?? {}),
    org: org ?? undefined,
    role: org?.role,
  });
  state.user = user;
  state.accessToken = res.access_token ?? null;
  state.refreshToken = res.refresh_token ?? null;
  state.orgId = org?.id ?? null;
  state.loading = false;
}

function clearSession(state: Partial<SessionState>) {
  clearAuth();
  state.user = null;
  state.accessToken = null;
  state.refreshToken = null;
  state.orgId = null;
  state.loading = false;
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      orgId: null,
      loading: true,

      login: async (email, password) => {
        const res = await authApi.login(email, password);
        set((s) => {
          const next = { ...s };
          applyAuth(next, res);
          return next;
        });
      },

      register: async (name, email, password) => {
        const res = await authApi.register({
          email,
          password,
          full_name: name,
        });
        set((s) => {
          const next = { ...s };
          applyAuth(next, res);
          return next;
        });
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // session is cleared regardless of network outcome
        }
        set((s) => {
          const next = { ...s };
          clearSession(next);
          return next;
        });
      },

      hydrate: async () => {
        try {
          const me = await authApi.me();
          set((s) => ({
            ...s,
            user: mapSessionUser(me as unknown as Record<string, unknown>),
            loading: false,
          }));
        } catch {
          set((s) => {
            const next = { ...s };
            clearSession(next);
            return next;
          });
        }
      },
    }),
    {
      name: "af-session",
      partialize: (s) => ({
        user: s.user,
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        orgId: s.orgId,
      }),
    },
  ),
);

// Global sign-out when the API client can no longer refresh the session.
if (typeof window !== "undefined") {
  window.addEventListener(UNAUTHORIZED_EVENT, () => {
    useSession.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      orgId: null,
      loading: false,
    });
  });
}
