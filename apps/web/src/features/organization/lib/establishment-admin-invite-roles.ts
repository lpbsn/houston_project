import type { RoleEnum } from '@/features/auth/types'

export type EstablishmentAdminInviteRole = 'director' | 'manager' | 'staff'

const OWNER_TARGETS: EstablishmentAdminInviteRole[] = ['director', 'manager', 'staff']
const DIRECTOR_TARGETS: EstablishmentAdminInviteRole[] = ['manager', 'staff']

export function getEstablishmentAdminInviteTargetRoles(
  actorRole: RoleEnum | null | undefined,
): EstablishmentAdminInviteRole[] {
  switch (actorRole) {
    case 'owner':
      return OWNER_TARGETS
    case 'director':
      return DIRECTOR_TARGETS
    default:
      return []
  }
}

export function establishmentAdminInviteRequiresScopes(
  role: EstablishmentAdminInviteRole | null | undefined,
) {
  return role === 'staff' || role === 'manager'
}
