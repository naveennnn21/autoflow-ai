import { Navbar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { BentoSection } from "@/components/landing/bento-section";
import { Storytelling } from "@/components/landing/storytelling";
import { ConnectorsShowcase } from "@/components/landing/connectors-showcase";
import { Testimonials, Pricing, Faq } from "@/components/landing/social";
import { Footer } from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <Navbar />
      <main>
        <Hero />
        <BentoSection />
        <Storytelling />
        <div className="section-light">
          <ConnectorsShowcase />
        </div>
        <Testimonials />
        <Pricing />
        <Faq />
      </main>
      <Footer />
    </div>
  );
}