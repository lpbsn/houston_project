import type { Membership } from '@/features/auth/types'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'

export function canSwitchEstablishment(
  memberships: Membership[],
  activeEstablishmentId: string | null | undefined,
): boolean {
  if (memberships.length <= 1) {
    return false
  }

  if (!activeEstablishmentId) {
    return memberships.length > 1
  }

  return memberships.some((membership) => membership.establishment_id !== activeEstablishmentId)
}

export function canOpenEstablishmentsHub({
  memberships,
  activeEstablishmentId,
  pendingOnboardingMemberships,
  canCreateEstablishment,
}: {
  memberships: Membership[]
  activeEstablishmentId: string | null | undefined
  pendingOnboardingMemberships: PendingOnboardingMembership[]
  canCreateEstablishment: boolean
}): boolean {
  return (
    canSwitchEstablishment(memberships, activeEstablishmentId) ||
    pendingOnboardingMemberships.length > 0 ||
    canCreateEstablishment
  )
}
