import { BackgroundEngine } from "@/components/motion/background-engine";
import { DotGrid } from "@/components/motion/dot-grid";
import { Logo } from "@/components/shared/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 py-12">
      <BackgroundEngine variant="atmospheric" particles={false} className="absolute inset-0" />
      <DotGrid className="opacity-30 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,black,transparent)]" />
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,transparent_0%,hsl(var(--background))_75%)]" />
      <div className="relative mb-10">
        <Logo />
      </div>
      <div className="relative w-full max-w-sm">{children}</div>
    </div>
  );
}