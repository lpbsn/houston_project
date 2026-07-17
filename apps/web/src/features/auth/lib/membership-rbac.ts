import type { RoleEnum } from '@/features/auth/types'

const MANAGEABLE_TARGET_ROLES_BY_ACTOR: Record<RoleEnum, RoleEnum[]> = {
  owner: ['owner', 'director', 'manager', 'staff'],
  director: ['manager', 'staff'],
  manager: ['staff', 'manager'],
  staff: [],
}

/** PATCH destinations never include owner or director. */
const PATCHABLE_ROLE_DESTINATIONS: RoleEnum[] = ['manager', 'staff']

export function canActorManageTargetRole(actorRole: RoleEnum, targetRole: RoleEnum) {
  return MANAGEABLE_TARGET_ROLES_BY_ACTOR[actorRole]?.includes(targetRole) ?? false
}

/**
 * Whether the membership's role may be changed via PATCH.
 * Owners are immutable via PATCH; directors may be demoted to manager/staff.
 */
export function canChangeMembershipRoleViaPatch(targetRole: RoleEnum) {
  return targetRole !== 'owner'
}

/**
 * Role destinations selectable via PATCH for this actor (and optional current target).
 * Never returns owner/director as destinations. Empty when target is already owner.
 */
export function getEditableRoleOptions(
  actorRole: RoleEnum,
  targetRole?: RoleEnum | null,
): RoleEnum[] {
  if (targetRole === 'owner') {
    return []
  }

  const manageable = MANAGEABLE_TARGET_ROLES_BY_ACTOR[actorRole] ?? []
  return PATCHABLE_ROLE_DESTINATIONS.filter((role) => manageable.includes(role))
}

export function canEditMembershipOperationalScopes(role: RoleEnum) {
  return role === 'staff' || role === 'manager'
}
