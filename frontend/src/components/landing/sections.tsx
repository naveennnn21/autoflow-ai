"use client";

import { Icon } from "@/components/shared/icons";
import { Marquee } from "@/components/motion/marquee";
import { FadeIn, StaggerGroup, StaggerItem } from "@/components/motion/fade-in";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { features, integrations } from "@/lib/mock-content";

export function Features() {
  return (
    <section id="features" className="relative py-24">
      <div className="container">
        <FadeIn className="mx-auto mb-14 max-w-2xl text-center">
          <Badge variant="gradient" className="mb-4">Features</Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
            Everything you need to automate
          </h2>
          <p className="mt-3 text-muted-foreground">
            From natural-language planning to enterprise-grade execution — one platform, end to end.
          </p>
        </FadeIn>
        <StaggerGroup className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <StaggerItem key={f.title}>
              <Card className="card-hover h-full group relative overflow-hidden">
                <div className={cn("pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-gradient-to-br opacity-20 blur-2xl transition-opacity group-hover:opacity-40", f.gradient)} />
                <CardContent className="p-6">
                  <div className={cn("mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-soft", f.gradient)}>
                    <Icon name={f.icon} className="h-5 w-5" />
                  </div>
                  <h3 className="mb-2 font-semibold">{f.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{f.description}</p>
                </CardContent>
              </Card>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </div>
    </section>
  );
}

export function Integrations() {
  return (
    <section id="integrations" className="relative py-24">
      <div className="container">
        <FadeIn className="mx-auto mb-12 max-w-2xl text-center">
          <Badge variant="gradient" className="mb-4">Integrations</Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">200+ connectors, zero friction</h2>
          <p className="mt-3 text-muted-foreground">
            Every connector ships with OAuth, automatic token refresh, rate limits, and retries built in.
          </p>
        </FadeIn>
        <Marquee>
          {integrations.map((i) => (
            <div key={i.name} className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-5 py-3 shadow-soft">
              <Icon name={i.logo} className="h-5 w-5" />
              <span className="text-sm font-medium">{i.name}</span>
            </div>
          ))}
        </Marquee>
      </div>
    </section>
  );
}
