import type { MembershipInvitationRequestRoleEnum, RoleEnum } from '@/features/auth/types'

const OWNER_DIRECTOR_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['staff', 'manager']
const MANAGER_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['staff']
const NO_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = []

export function getAllowedInviteTargetRoles(
  actorRole: RoleEnum | null | undefined,
): MembershipInvitationRequestRoleEnum[] {
  switch (actorRole) {
    case 'owner':
      return OWNER_DIRECTOR_TARGET_ROLES
    case 'director':
      return OWNER_DIRECTOR_TARGET_ROLES
    case 'manager':
      return MANAGER_TARGET_ROLES
    case 'staff':
    default:
      return NO_TARGET_ROLES
  }
}

export function canSeeInviteMemberButton(role: RoleEnum | null | undefined) {
  return getAllowedInviteTargetRoles(role).length > 0
}

export function canAccessTeamInvite(role: RoleEnum | null | undefined) {
  return getAllowedInviteTargetRoles(role).length > 0
}
