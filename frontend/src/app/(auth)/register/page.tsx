"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { Github, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useSession } from "@/stores/session";
import { toast } from "sonner";

export default function RegisterPage() {
  const router = useRouter();
  const login = useSession((s) => s.login);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) return;
    setLoading(true);
    await login(email);
    toast.success("Workspace created", { description: `Welcome, ${name}!` });
    router.push("/dashboard");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="mb-8 text-center">
        <p className="text-section text-balance leading-[1.05]">Build something automatic.</p>
        <p className="mt-3 text-sm text-muted-foreground">Create your workspace. Free forever plan included.</p>
      </div>

      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="name" className="text-xs font-medium">Full name</Label>
          <Input id="name" placeholder="Ada Lovelace" value={name} onChange={(e) => setName(e.target.value)} required className="h-11" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-xs font-medium">Work email</Label>
          <Input id="email" type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required className="h-11" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password" className="text-xs font-medium">Password</Label>
          <Input id="password" type="password" placeholder="8+ characters" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" minLength={8} required className="h-11" />
        </div>
        <Button type="submit" className="w-full h-11" disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Creating..." : "Create workspace"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3">
        <Separator className="flex-1" />
        <span className="text-xs text-muted-foreground">or</span>
        <Separator className="flex-1" />
      </div>

      <Button variant="outline" className="w-full h-10" disabled={loading}>
        <Github className="h-4 w-4" /> Continue with GitHub
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-foreground hover:underline">Sign in</Link>
      </p>
    </motion.div>
  );
}