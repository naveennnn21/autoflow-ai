/**
 * AutoFlow AI - core API client.
 *
 * Single fetch wrapper used by every domain module under lib/api/.
 *   - resolves the backend base URL from NEXT_PUBLIC_API_URL
 *   - injects the Bearer token and X-Org-Id header for tenant isolation
 *   - transparently refreshes the access token once on a 401
 *   - normalizes non-2xx responses into ApiError
 *   - emits an "autoflow:unauthorized" event when the session can no longer
 *     be refreshed (the session store listens and signs the user out)
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const UNAUTHORIZED_EVENT = "autoflow:unauthorized";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** In-memory token holder, seeded lazily from the persisted session store. */
interface TokenState {
  accessToken: string | null;
  refreshToken: string | null;
  orgId: string | null;
}

let tokens: TokenState = { accessToken: null, refreshToken: null, orgId: null };

export function setAccessToken(token: string | null): void {
  tokens.accessToken = token;
}

export function setRefreshToken(token: string | null): void {
  tokens.refreshToken = token;
}

export function setOrgId(orgId: string | null): void {
  tokens.orgId = orgId;
}

export function getAccessToken(): string | null {
  return tokens.accessToken;
}

export function getOrgId(): string | null {
  return tokens.orgId;
}

export function clearAuth(): void {
  tokens = { accessToken: null, refreshToken: null, orgId: null };
}

/**
 * Lazily hydrate module tokens from the persisted zustand session store
 * ("af-session") so the first request after a reload already carries auth
 * without waiting for the store to hydrate.
 */
export function hydrateFromStorage(): TokenState {
  if (tokens.accessToken || typeof window === "undefined") return tokens;
  try {
    const raw = window.localStorage.getItem("af-session");
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: Partial<TokenState> };
      const state = parsed.state ?? {};
      tokens = {
        accessToken: state.accessToken ?? null,
        refreshToken: state.refreshToken ?? null,
        orgId: state.orgId ?? null,
      };
    }
  } catch {
    // corrupted storage - fall through with empty tokens
  }
  return tokens;
}

function emitUnauthorized(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const state = hydrateFromStorage();
  if (!state.refreshToken) return null;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { access_token?: string };
    if (!data.access_token) return null;
    setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Set false to skip the bearer token (e.g. auth endpoints). */
  auth?: boolean;
}

export async function request<T>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {}, auth = true } = opts;
  const state = hydrateFromStorage();

  const build = (token: string | null) => ({
    method,
    headers: {
      "Content-Type": "application/json",
      ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
      ...(state.orgId ? { "X-Org-Id": state.orgId } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store" as RequestCache,
  });

  // One retry for transient failures (network blips, gateway 5xx).
  const attempt = async (token: string | null, retried: boolean): Promise<Response> => {
    const res = await fetch(`${API_URL}${path}`, build(token));
    if (!retried && (res.status === 502 || res.status === 503 || res.status === 504)) {
      await new Promise((r) => setTimeout(r, 400));
      return attempt(token, true);
    }
    return res;
  };

  let res: Response;
  try {
    res = await attempt(state.accessToken, false);
  } catch {
    if (!auth) throw new ApiError(0, "Network request failed");
    await new Promise((r) => setTimeout(r, 400));
    try {
      res = await attempt(state.accessToken, true);
    } catch {
      throw new ApiError(0, "Network request failed");
    }
  }

  if (res.status === 401 && auth) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      res = await attempt(fresh, true);
    } else {
      clearAuth();
      emitUnauthorized();
    }
  }

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    let detail: unknown;
    try {
      const data = (await res.json()) as { detail?: unknown; message?: string };
      if (typeof data.detail === "string") message = data.detail;
      else if (typeof data.message === "string") message = data.message;
      detail = data.detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(res.status, message, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function withQuery(
  path: string,
  params: object,
): string {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return qs ? `${path}?${qs}` : path;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PUT", body }),
  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "DELETE" }),
};
