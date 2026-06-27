import type { Membership } from '@/features/auth/types'

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
