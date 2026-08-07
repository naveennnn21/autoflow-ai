"use client";

import { api } from "./client";
import type { AuthResponse, BackendUser } from "@/types";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>(
      "/auth/login",
      { email, password },
      { auth: false },
    ),

  register: (payload: RegisterPayload) =>
    api.post<AuthResponse>("/auth/register", payload, { auth: false }),

  me: () => api.get<BackendUser>("/auth/me"),

  logout: () => api.post<{ detail: string }>("/auth/logout"),

  refresh: (refreshToken: string) =>
    api.post<{ access_token: string; token_type: string }>(
      "/auth/refresh",
      { refresh_token: refreshToken },
      { auth: false },
    ),

  passwordChange: (oldPassword: string, newPassword: string) =>
    api.post<{ detail: string }>("/auth/password-change", {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};
