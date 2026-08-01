"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "sonner";
import { MeshBackground } from "@/components/motion/mesh-background";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="dark"
        enableSystem
        disableTransitionOnChange
      >
        <div className="relative flex min-h-screen flex-col">
          <MeshBackground intensity="subtle" className="fixed inset-0 -z-10" />
          <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 bg-noise" />
          <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,hsl(var(--primary)/0.08),transparent_55%)]" />
          <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
        </div>
        <Toaster
          position="bottom-right"
          theme="system"
          toastOptions={{
            style: {
              background: "hsl(var(--popover))",
              color: "hsl(var(--popover-foreground))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "var(--radius)",
              boxShadow: "0 24px 80px -24px rgba(0, 0, 0, 0.5)",
            },
          }}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
