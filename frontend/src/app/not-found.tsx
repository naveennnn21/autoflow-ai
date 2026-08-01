import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-glow">
        <Compass className="h-7 w-7" />
      </div>
      <div className="space-y-2">
        <p className="text-6xl font-bold tracking-tight gradient-text">404</p>
        <h1 className="text-xl font-semibold">This flow doesn&apos;t exist</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          The page you&apos;re looking for was moved, renamed, or never compiled.
        </p>
      </div>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/dashboard">Back to dashboard</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/">Home</Link>
        </Button>
      </div>
    </div>
  );
}
