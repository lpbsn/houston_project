import { LandingAgent } from '@/features/landing/components/landing-agent'
import { LandingContact } from '@/features/landing/components/landing-contact'
import { LandingFooter } from '@/features/landing/components/landing-footer'
import { LandingHeader } from '@/features/landing/components/landing-header'
import { LandingHero } from '@/features/landing/components/landing-hero'
import { LandingPricing } from '@/features/landing/components/landing-pricing'
import { LandingProblem } from '@/features/landing/components/landing-problem'

export function LandingPage() {
  return (
    <div id="spore-landing" data-testid="landing-page">
      <LandingHeader />
      <LandingHero />
      <LandingProblem />
      <LandingAgent />
      <LandingPricing />
      <LandingContact />
      <LandingFooter />
    </div>
  )
}
