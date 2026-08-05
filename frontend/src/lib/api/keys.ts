/** Centralized TanStack Query cache keys. */
export const queryKeys = {
  workflows: ["workflows"] as const,
  workflow: (id: string) => ["workflows", id] as const,
  executions: ["executions"] as const,
  metrics: ["metrics"] as const,
  alerts: ["alerts"] as const,
  health: ["health"] as const,
  activity: ["activity"] as const,
  connectors: ["connectors"] as const,
  connector: (slug: string) => ["connectors", slug] as const,
  organizations: ["organizations"] as const,
  organization: (id: string) => ["organizations", id] as const,
  apiKeys: ["api-keys"] as const,
  notifications: ["notifications"] as const,
  teams: ["teams"] as const,
  users: ["users"] as const,
  subscriptions: ["subscriptions"] as const,
};
