import type { Metadata, Viewport } from "next";
import "@fontsource-variable/rubik";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Providers } from "@/providers/providers";

export const metadata: Metadata = {
  title: {
    default: "AutoFlow AI — Automations that build themselves",
    template: "%s · AutoFlow AI",
  },
  description:
    "Describe what you want in plain English. AutoFlow's AI planner designs the workflow, compiles a validated spec, and connects 200+ tools.",
  keywords: ["automation", "AI", "workflows", "connectors", "SaaS"],
  openGraph: {
    title: "AutoFlow AI",
    description: "Automations that build themselves.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0B1018",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
