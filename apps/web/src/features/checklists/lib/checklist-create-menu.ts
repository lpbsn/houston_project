import type { RoleEnum } from '@/features/auth/types'

import { canSeeSharedChecklistManagement } from './checklist-management-access'

export type ChecklistCreateMenuOptionId = 'shared' | 'personal'

export type ChecklistCreateMenuOption = {
  id: ChecklistCreateMenuOptionId
  label: string
}

export function getChecklistCreateMenuOptions(
  role: string | null | undefined,
): ChecklistCreateMenuOption[] {
  const normalizedRole = role as RoleEnum | null | undefined
  const options: ChecklistCreateMenuOption[] = []

  if (canSeeSharedChecklistManagement(normalizedRole)) {
    options.push({ id: 'shared', label: 'Checklist partagée' })
  }

  options.push({ id: 'personal', label: 'Checklist personnelle' })

  return options
}
