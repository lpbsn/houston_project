import type { RoleEnum } from '@/features/auth/types'
import type { BootstrapResponse } from '@/features/auth/types'
import { toRoleEnum } from '@/features/auth/lib/role'

export function canAccessEstablishmentAdminPage({
  canManageOrganization,
  memberships,
  establishmentId,
}: {
  canManageOrganization: boolean
  memberships: BootstrapResponse['memberships'] | null | undefined
  establishmentId: string
}): boolean {
  if (canManageOrganization) {
    return true
  }

  return (memberships ?? []).some(
    (membership) =>
      membership.establishment_id === establishmentId &&
      membership.status === 'active' &&
      toRoleEnum(membership.role) === 'director',
  )
}

export function resolveEstablishmentAdminActorRole({
  canManageOrganization,
  memberships,
  establishmentId,
}: {
  canManageOrganization: boolean
  memberships: BootstrapResponse['memberships'] | null | undefined
  establishmentId: string
}): RoleEnum | null {
  if (canManageOrganization) {
    return 'owner'
  }

  const directorMembership = (memberships ?? []).find(
    (membership) =>
      membership.establishment_id === establishmentId &&
      membership.status === 'active' &&
      toRoleEnum(membership.role) === 'director',
  )
  return directorMembership ? 'director' : null
}
