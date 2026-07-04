import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

export type ExecutionCreateMenuOptionId = 'action_plan'

export type ExecutionCreateMenuOption = {
  id: ExecutionCreateMenuOptionId
  label: string
  disabled: boolean
  badge?: string
}

export function getExecutionCreateMenuOptions(
  permissionHints: BootstrapPermissionHints | null | undefined,
): ExecutionCreateMenuOption[] {
  if (permissionHints?.can_create_action_plan !== true) {
    return []
  }

  return [
    {
      id: 'action_plan',
      label: "Plan d'action",
      disabled: false,
    },
  ]
}

export function canOpenExecutionCreateMenu(
  permissionHints: BootstrapPermissionHints | null | undefined,
): boolean {
  return permissionHints?.can_create_action_plan === true
}
