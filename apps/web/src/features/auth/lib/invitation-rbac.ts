import type { MembershipInvitationRequestRoleEnum, RoleEnum } from '@/features/auth/types'

/** Session `/team` invite matrix — Owner invites go via `/organization` only. */
const OWNER_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = [
  'director',
  'manager',
  'staff',
]
const DIRECTOR_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['manager', 'staff']
const MANAGER_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['staff']
const NO_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = []

export function getAllowedInviteTargetRoles(
  actorRole: RoleEnum | null | undefined,
): MembershipInvitationRequestRoleEnum[] {
  switch (actorRole) {
    case 'owner':
      return OWNER_TARGET_ROLES
    case 'director':
      return DIRECTOR_TARGET_ROLES
    case 'manager':
      return MANAGER_TARGET_ROLES
    case 'staff':
    default:
      return NO_TARGET_ROLES
  }
}

export function requiresInviteScopes(role: MembershipInvitationRequestRoleEnum | null | undefined) {
  return role === 'staff' || role === 'manager'
}
