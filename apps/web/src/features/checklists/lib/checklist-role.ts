import type { RoleEnum } from '@/features/auth/types'

const ACTIVE_ROLES: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

export function toRoleEnum(role: string | null | undefined): RoleEnum | null {
  if (!role) {
    return null
  }

  return ACTIVE_ROLES.find((candidate) => candidate === role) ?? null
}
