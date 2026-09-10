import type { MembershipInvitationRequestRoleEnum, RoleEnum } from '@/features/auth/types'

/** Membership invite matrix. Owner uses `POST …/owner-invitations/` from `/team/invite`. */
export type TeamInviteRoleOption = 'owner' | MembershipInvitationRequestRoleEnum

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

export function resolveTeamInviteRoleOptions({
  actorRole,
  canManageOrganization,
}: {
  actorRole: RoleEnum | null | undefined
  canManageOrganization: boolean
}): TeamInviteRoleOption[] {
  const membershipRoles = getAllowedInviteTargetRoles(actorRole)
  if (canManageOrganization) {
    return ['owner', ...membershipRoles]
  }
  return membershipRoles
}

export function requiresInviteScopes(role: TeamInviteRoleOption | null | undefined) {
  return role === 'staff' || role === 'manager'
}
