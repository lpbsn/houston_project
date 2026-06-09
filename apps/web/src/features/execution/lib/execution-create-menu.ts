export type ExecutionCreateMenuOptionId = 'action' | 'flash_todo' | 'checklist'

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
  role: string | null | undefined,
): ExecutionCreateMenuOption[] {
  const canCreateAction = role === 'owner' || role === 'director' || role === 'manager'

  const options: ExecutionCreateMenuOption[] = []

  if (canCreateAction) {
    options.push({
      id: 'action',
      label: 'Action',
      disabled: false,
    })
  }

  options.push({
    id: 'flash_todo',
    label: 'Flash To-do',
    disabled: false,
  })

  options.push({
    id: 'checklist',
    label: 'Checklist',
    disabled: false,
  })

  return options
}

export function getChecklistCreateSubmenuOptions(): ChecklistCreateSubmenuOption[] {
  return [
    { id: 'create_registered', label: 'Créer une checklist' },
    { id: 'use_existing', label: 'Utiliser une checklist existante' },
  ]
}

export function canOpenExecutionCreateMenu(role: string | null | undefined): boolean {
  return Boolean(role)
}
