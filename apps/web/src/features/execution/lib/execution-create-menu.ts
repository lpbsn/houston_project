export type ExecutionCreateMenuOptionId = 'action' | 'checklist'

export type ExecutionCreateMenuOption = {
  id: ExecutionCreateMenuOptionId
  label: string
  disabled: boolean
  badge?: string
}

export const EXECUTION_CREATE_MENU_OPTIONS: ExecutionCreateMenuOption[] = [
  {
    id: 'action',
    label: 'Action',
    disabled: false,
  },
  {
    id: 'checklist',
    label: 'Checklist',
    disabled: true,
    badge: 'Bientôt',
  },
]

export function getExecutionCreateMenuOption(
  id: ExecutionCreateMenuOptionId,
): ExecutionCreateMenuOption | undefined {
  return EXECUTION_CREATE_MENU_OPTIONS.find((option) => option.id === id)
}
