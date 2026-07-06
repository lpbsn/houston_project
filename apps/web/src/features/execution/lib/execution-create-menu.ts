import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

export type ExecutionCreateMenuOptionId = 'action_plan' | 'catalog'

export type ExecutionCreateMenuOption = {
  id: ExecutionCreateMenuOptionId
  label: string
  disabled: boolean
  badge?: string
}

export function getExecutionCreateMenuOptions(
  permissionHints: BootstrapPermissionHints | null | undefined,
): ExecutionCreateMenuOption[] {
  const options: ExecutionCreateMenuOption[] = []

  if (permissionHints?.can_create_action_plan === true) {
    options.push({
      id: 'action_plan',
      label: "Créer un plan d'action",
      disabled: false,
    })
  }

  if (permissionHints?.can_view_action_plan_catalog === true) {
    options.push({
      id: 'catalog',
      label: 'Choisir un modèle existant',
      disabled: false,
    })
  }

  return options
}

export function canOpenExecutionCreateMenu(
  permissionHints: BootstrapPermissionHints | null | undefined,
): boolean {
  return getExecutionCreateMenuOptions(permissionHints).length > 0
}
