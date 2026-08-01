"use client";

import { Github, Twitter, Linkedin } from "lucide-react";
import { Logo } from "@/components/shared/logo";

const columns = [
  {
    title: "Product",
    links: ["AI Planner", "Workflow Builder", "Connectors", "Analytics", "Pricing"],
  },
  {
    title: "Resources",
    links: ["Documentation", "API Reference", "Changelog", "Status", "Community"],
  },
  {
    title: "Company",
    links: ["About", "Blog", "Careers", "Contact", "Security"],
  },
];

const socials = [
  { icon: Github, label: "GitHub" },
  { icon: Twitter, label: "Twitter" },
  { icon: Linkedin, label: "LinkedIn" },
];

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-border/60 bg-background/60 backdrop-blur-xl">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
      <div className="container py-14">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Logo />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              The AI automation platform that designs, compiles, and runs your workflows — from a single sentence.
            </p>
            <div className="mt-5 flex gap-2">
              {socials.map(({ icon: Icon, label }) => (
                <a
                  key={label}
                  href="#"
                  aria-label={label}
                  className="group flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition-all hover:border-primary/40 hover:text-foreground hover:shadow-[0_0_20px_-6px_hsl(var(--primary)/0.5)]"
                >
                  <Icon className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
                </a>
              ))}
            </div>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <h3 className="text-sm font-semibold">{col.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border/60 pt-6 sm:flex-row">
          <p className="text-xs text-muted-foreground">© 2026 AutoFlow AI, Inc. All rights reserved.</p>
          <div className="flex items-center gap-5 text-xs text-muted-foreground">
            <a href="#" className="transition-colors hover:text-foreground">Privacy</a>
            <a href="#" className="transition-colors hover:text-foreground">Terms</a>
            <a href="#" className="transition-colors hover:text-foreground">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
