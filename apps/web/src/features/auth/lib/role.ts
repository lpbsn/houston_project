import type { RoleEnum } from '@/features/auth/types'

export const INVITATION_ROLES: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

export function toRoleEnum(role: string | null | undefined): RoleEnum | null {
  if (!role) {
    return null
  }

  return INVITATION_ROLES.find((candidate) => candidate === role) ?? null
}
