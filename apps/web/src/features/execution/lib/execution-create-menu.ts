export type ExecutionCreateMenuOptionId = 'action' | 'personal_checklist'

export type ExecutionCreateMenuOption = {
  id: ExecutionCreateMenuOptionId
  label: string
  disabled: boolean
  badge?: string
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
    id: 'personal_checklist',
    label: 'Checklist personnelle',
    disabled: false,
  })

  return options
}

export function canOpenExecutionCreateMenu(role: string | null | undefined): boolean {
  return Boolean(role)
}
