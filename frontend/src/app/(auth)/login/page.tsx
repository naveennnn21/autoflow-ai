"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { Github, Loader2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useSession } from "@/stores/session";
import { toast } from "sonner";

export default function LoginPage() {
  const router = useRouter();
  const login = useSession((s) => s.login);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    await login(email);
    toast.success("Welcome back");
    router.push("/dashboard");
  };

  const magicLink = async () => {
    if (!email) { toast.error("Enter your email first"); return; }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 900));
    toast.success("Magic link sent", { description: `Check ${email}` });
    setLoading(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="mb-8 text-center">
        <p className="text-section text-balance leading-[1.05]">Build something automatic.</p>
        <p className="mt-3 text-sm text-muted-foreground">Sign in to your workspace.</p>
      </div>

      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-xs font-medium">Work email</Label>
          <Input id="email" type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required className="h-11" />
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-xs font-medium">Password</Label>
            <Link href="/login" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Forgot?</Link>
          </div>
          <Input id="password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required className="h-11" />
        </div>
        <Button type="submit" className="w-full h-11" disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3">
        <Separator className="flex-1" />
        <span className="text-xs text-muted-foreground">or</span>
        <Separator className="flex-1" />
      </div>

      <div className="space-y-2">
        <Button variant="outline" className="w-full h-10" onClick={magicLink} disabled={loading}>
          <Mail className="h-4 w-4" /> Magic link
        </Button>
        <Button variant="outline" className="w-full h-10" disabled={loading}>
          <Github className="h-4 w-4" /> GitHub
        </Button>
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        New to AutoFlow?{" "}
        <Link href="/register" className="font-medium text-foreground hover:underline">Create an account</Link>
      </p>
    </motion.div>
  );
}