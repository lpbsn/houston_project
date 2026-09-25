import { useCallback, useState } from 'react'

import { LandingAgent } from '@/features/landing/components/landing-agent'
import { LandingFooter } from '@/features/landing/components/landing-footer'
import { LandingHeader } from '@/features/landing/components/landing-header'
import { LandingHero } from '@/features/landing/components/landing-hero'
import { LandingPricing } from '@/features/landing/components/landing-pricing'
import { LandingProblem } from '@/features/landing/components/landing-problem'

export function LandingPage() {
  const [demoOpen, setDemoOpen] = useState(false)

  const openDemo = useCallback(() => {
    setDemoOpen(true)
  }, [])

  const closeDemo = useCallback(() => {
    setDemoOpen(false)
  }, [])

  return (
    <div id="spore-landing" data-testid="landing-page">
      <LandingHeader onDemo={openDemo} />
      <LandingHero onDemo={openDemo} />
      <LandingProblem />
      <LandingAgent />
      <LandingPricing demoOpen={demoOpen} onDemo={openDemo} onCloseDemo={closeDemo} />
      <LandingFooter />
    </div>
  )
}
