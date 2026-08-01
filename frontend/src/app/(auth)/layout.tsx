import { AuroraBackground } from "@/components/motion/aurora-background";
import { Particles } from "@/components/motion/particles";
import { LightBeams } from "@/components/motion/light-beams";
import { GradientOrb } from "@/components/motion/gradient-orb";
import { Logo } from "@/components/shared/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 py-12">
      <AuroraBackground />
      <Particles className="opacity-40" />
      <LightBeams />
      <GradientOrb color="primary" className="left-[12%] top-[15%] size-72" />
      <GradientOrb color="accent" className="right-[10%] top-[40%] size-80" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,transparent_0%,hsl(var(--background))_75%)]" />
      <div className="relative mb-8">
        <Logo />
      </div>
      <div className="relative w-full max-w-md">{children}</div>
    </div>
  );
}
