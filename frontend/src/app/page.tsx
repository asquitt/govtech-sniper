"use client";

import { LandingNav } from "./_components/landing-nav";
import { HeroSection } from "./_components/hero-section";
import { SocialProofBar } from "./_components/social-proof-bar";
import { PainPointsSection } from "./_components/pain-points-section";
import { FeatureGrid } from "./_components/feature-grid";
import { HowItWorks } from "./_components/how-it-works";
import { StatsSection } from "./_components/stats-section";
import { SecuritySection } from "./_components/security-section";
import { FinalCta } from "./_components/final-cta";
import { LandingFooter } from "./_components/landing-footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-background overflow-x-hidden">
      <LandingNav />
      <HeroSection />
      <SocialProofBar />
      <PainPointsSection />
      <FeatureGrid />
      <HowItWorks />
      <StatsSection />
      <SecuritySection />
      <FinalCta />
      <LandingFooter />
    </main>
  );
}
