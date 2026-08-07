import { AppShell } from "@/components/layout/app-shell";
import { RequireAuth } from "@/components/auth/guards";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
