import type { RoleEnum } from '@/features/auth/types'

export function canSeeChecklistLibrary(role: RoleEnum | null | undefined): boolean {
  return Boolean(role)
}
