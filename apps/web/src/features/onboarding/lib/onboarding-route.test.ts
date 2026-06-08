import { describe, expect, it } from 'vitest'

import { shouldRedirectOnboardingToOperationalConfig } from '@/features/onboarding/lib/onboarding-route'

describe('shouldRedirectOnboardingToOperationalConfig', () => {
  const activeEstablishmentId = '33333333-3333-3333-3333-333333333333'

  it('redirects when user has operational access on the same establishment', () => {
    expect(
      shouldRedirectOnboardingToOperationalConfig({
        hasOperationalAccess: true,
        activeEstablishmentId,
        routeEstablishmentId: activeEstablishmentId,
      }),
    ).toBe(true)
  })

  it('does not redirect without operational access', () => {
    expect(
      shouldRedirectOnboardingToOperationalConfig({
        hasOperationalAccess: false,
        activeEstablishmentId,
        routeEstablishmentId: activeEstablishmentId,
      }),
    ).toBe(false)
  })

  it('does not redirect when route establishment differs', () => {
    expect(
      shouldRedirectOnboardingToOperationalConfig({
        hasOperationalAccess: true,
        activeEstablishmentId,
        routeEstablishmentId: '44444444-4444-4444-4444-444444444444',
      }),
    ).toBe(false)
  })

  it('does not redirect without route establishment id', () => {
    expect(
      shouldRedirectOnboardingToOperationalConfig({
        hasOperationalAccess: true,
        activeEstablishmentId,
        routeEstablishmentId: null,
      }),
    ).toBe(false)
  })
})
