import type { RoleEnum } from '@/features/auth/types'

const MANAGEABLE_TARGET_ROLES_BY_ACTOR: Record<RoleEnum, RoleEnum[]> = {
  owner: ['owner', 'director', 'manager', 'staff'],
  director: ['manager', 'staff'],
  manager: [],
  staff: [],
}

export function canActorManageTargetRole(actorRole: RoleEnum, targetRole: RoleEnum) {
  return MANAGEABLE_TARGET_ROLES_BY_ACTOR[actorRole]?.includes(targetRole) ?? false
}

export function getEditableRoleOptions(actorRole: RoleEnum): RoleEnum[] {
  return MANAGEABLE_TARGET_ROLES_BY_ACTOR[actorRole] ?? []
}

export function canEditMembershipOperationalScopes(role: RoleEnum) {
  return role === 'staff' || role === 'manager'
}
