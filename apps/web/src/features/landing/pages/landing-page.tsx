import { DirectionSection } from '@/features/landing/components/direction-section'
import { FinalCtaSection, LandingFooter } from '@/features/landing/components/final-cta-section'
import { HeroSection } from '@/features/landing/components/hero-section'
import { HowItWorksSection } from '@/features/landing/components/how-it-works-section'
import { PricingSection } from '@/features/landing/components/pricing-section'
import { ProblemSwarmSection } from '@/features/landing/components/problem-swarm-section'
import { SoonAvailableProvider } from '@/features/landing/components/soon-available-provider'
import { TransitionSolutionSection } from '@/features/landing/components/transition-solution-section'

export function LandingPage() {
  return (
    <SoonAvailableProvider>
      {({ openSoon }) => (
        <div data-testid="landing-page" className="min-h-dvh bg-white">
          <main>
            <HeroSection onCta={openSoon} />
            <ProblemSwarmSection />
            <TransitionSolutionSection />
            <HowItWorksSection />
            <DirectionSection />
            <PricingSection onCta={openSoon} />
            <FinalCtaSection onCta={openSoon} />
          </main>
          <LandingFooter />
        </div>
      )}
    </SoonAvailableProvider>
  )
}
