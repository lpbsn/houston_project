import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

export type ExecutionCreateMenuOptionId = 'action' | 'checklist'

export type ChecklistCreateSubmenuOptionId = 'create_registered' | 'use_existing'

export type ExecutionCreateMenuOption = {
  id: ExecutionCreateMenuOptionId
  label: string
  disabled: boolean
  badge?: string
}

export type ChecklistCreateSubmenuOption = {
  id: ChecklistCreateSubmenuOptionId
  label: string
}

export function getExecutionCreateMenuOptions(
  permissionHints: BootstrapPermissionHints | null | undefined,
): ExecutionCreateMenuOption[] {
  const canCreateAction = permissionHints?.can_create_action === true

  const options: ExecutionCreateMenuOption[] = []

  if (canCreateAction) {
    options.push({
      id: 'action',
      label: 'Action',
      disabled: false,
    })
  }

  options.push({
    id: 'checklist',
    label: 'Checklist',
    disabled: false,
  })

  return options
}

export function getChecklistCreateSubmenuOptions(
  permissionHints: BootstrapPermissionHints | null | undefined,
): ChecklistCreateSubmenuOption[] {
  const options: ChecklistCreateSubmenuOption[] = []

  if (permissionHints?.can_create_checklist_template === true) {
    options.push({ id: 'create_registered', label: 'Créer une checklist' })
  }

  options.push({ id: 'use_existing', label: 'Utiliser une checklist existante' })

  return options
}

export function canOpenExecutionCreateMenu(
  permissionHints: BootstrapPermissionHints | null | undefined,
): boolean {
  if (permissionHints == null) {
    return false
  }

  if (permissionHints.can_create_action === true) {
    return true
  }

  if (permissionHints.can_create_checklist_template === true) {
    return true
  }

  return getChecklistCreateSubmenuOptions(permissionHints).some(
    (option) => option.id === 'use_existing',
  )
}
