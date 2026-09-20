import type { BootstrapResponse } from '@/features/auth/types'

export type PendingOnboardingMembership =
  BootstrapResponse['pending_onboarding_memberships'][number]

export type PendingLandingKind = 'waiting' | 'selection' | 'none'

export type PendingLandingResolution =
  | { kind: 'none' }
  | { kind: 'waiting'; pending: PendingOnboardingMembership }
  | { kind: 'selection'; pendingMemberships: PendingOnboardingMembership[] }

export function resolvePendingLanding(
  pendingMemberships: PendingOnboardingMembership[],
): PendingLandingResolution {
  if (pendingMemberships.length === 0) {
    return { kind: 'none' }
  }

  if (pendingMemberships.length > 1) {
    return { kind: 'selection', pendingMemberships }
  }

  return { kind: 'waiting', pending: pendingMemberships[0]! }
}

export function resolvePendingLandingPath(
  pendingMemberships: PendingOnboardingMembership[],
): string | null {
  const landing = resolvePendingLanding(pendingMemberships)

  switch (landing.kind) {
    case 'waiting':
    case 'selection':
      return '/pending-onboarding'
    case 'none':
      return null
  }
}
