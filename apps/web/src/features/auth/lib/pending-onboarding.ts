import type { BootstrapResponse } from '@/features/auth/types'

export type PendingOnboardingMembership =
  BootstrapResponse['pending_onboarding_memberships'][number]

export type PendingLandingKind = 'onboarding' | 'waiting' | 'selection' | 'none'

export type PendingLandingResolution =
  | { kind: 'none' }
  | { kind: 'onboarding'; pending: PendingOnboardingMembership }
  | { kind: 'waiting'; pending: PendingOnboardingMembership }
  | { kind: 'selection'; pendingMemberships: PendingOnboardingMembership[] }

export function buildOnboardingUrl(pending: PendingOnboardingMembership) {
  const params = new URLSearchParams({
    establishmentId: pending.establishment_id,
  })

  if (pending.onboarding_session_id) {
    params.set('sessionId', pending.onboarding_session_id)
  }

  return `/onboarding?${params.toString()}`
}

export function resolvePendingLanding(
  pendingMemberships: PendingOnboardingMembership[],
): PendingLandingResolution {
  if (pendingMemberships.length === 0) {
    return { kind: 'none' }
  }

  if (pendingMemberships.length > 1) {
    return { kind: 'selection', pendingMemberships }
  }

  const pending = pendingMemberships[0]!

  if (pending.can_continue_onboarding) {
    return { kind: 'onboarding', pending }
  }

  return { kind: 'waiting', pending }
}

export function resolvePendingLandingPath(
  pendingMemberships: PendingOnboardingMembership[],
): string | null {
  const landing = resolvePendingLanding(pendingMemberships)

  switch (landing.kind) {
    case 'onboarding':
      return buildOnboardingUrl(landing.pending)
    case 'waiting':
    case 'selection':
      return '/pending-onboarding'
    case 'none':
      return null
  }
}
