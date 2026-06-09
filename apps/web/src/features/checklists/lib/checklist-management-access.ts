import type { RoleEnum } from '@/features/auth/types'

const SHARED_CHECKLIST_MANAGEMENT_ROLES = new Set<RoleEnum>([
  'owner',
  'director',
  'manager',
])

export function canSeeSharedChecklistManagement(role: RoleEnum | null | undefined): boolean {
  return Boolean(role && SHARED_CHECKLIST_MANAGEMENT_ROLES.has(role))
}

export function canSeePersonalChecklistManagement(role: RoleEnum | null | undefined): boolean {
  return Boolean(role)
}
