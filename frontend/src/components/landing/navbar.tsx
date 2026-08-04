"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { label: "Product", href: "/#product" },
  { label: "Solutions", href: "/#solutions" },
  { label: "Integrations", href: "/#integrations" },
  { label: "Developers", href: "/#developers" },
  { label: "Pricing", href: "/#pricing" },
];

export function Navbar() {
  const [scrolled, setScrolled] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const pathname = usePathname();
  const isLanding = pathname === "/";

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -48, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-500",
        scrolled
          ? "border-b border-border/50 bg-background/65 shadow-[0_12px_48px_-24px_rgba(0,0,0,0.6)] backdrop-blur-xl supports-[backdrop-filter]:bg-background/60"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="container flex h-16 items-center justify-between sm:h-[4.5rem]">
        <Logo />

        <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Primary">
          {links.map((l) => (
            <Link
              key={l.label}
              href={isLanding ? l.href : l.href.replace("#", "/#")}
              className="group relative rounded-full px-3.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {l.label}
              <span className="absolute inset-x-3.5 -bottom-px h-px origin-left scale-x-0 bg-foreground/60 transition-transform duration-300 group-hover:scale-x-100" />
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild size="sm" className="shadow-[0_4px_20px_-8px_hsl(var(--primary)/0.6)]">
            <Link href="/register">Get started</Link>
          </Button>
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          <Button variant="ghost" size="icon-sm" onClick={() => setOpen(!open)} aria-label="Toggle menu" aria-expanded={open}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {open && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
          className="border-t border-border/60 bg-background/95 px-4 pb-6 pt-2 backdrop-blur-2xl lg:hidden"
        >
          <nav className="flex flex-col gap-1" aria-label="Mobile">
            {links.map((l) => (
              <Link
                key={l.label}
                href={isLanding ? l.href : l.href.replace("#", "/#")}
                onClick={() => setOpen(false)}
                className="rounded-xl px-3 py-2.5 text-base font-medium transition-colors hover:bg-muted/70"
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <div className="mt-4 flex gap-2">
            <Button variant="outline" className="flex-1" asChild>
              <Link href="/login" onClick={() => setOpen(false)}>Sign in</Link>
            </Button>
            <Button className="flex-1" asChild>
              <Link href="/register" onClick={() => setOpen(false)}>Get started</Link>
            </Button>
          </div>
        </motion.div>
      )}
    </motion.header>
  );
}
