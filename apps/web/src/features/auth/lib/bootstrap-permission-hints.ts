import type { BootstrapResponse } from '@/features/auth/types'

export type BootstrapPermissionHints = BootstrapResponse['permission_hints']

const EMPTY_BOOTSTRAP_PERMISSION_HINTS: BootstrapPermissionHints = {
  chat_available: false,
  can_create_action: false,
  can_create_checklist_template: false,
  can_invite: false,
  can_manage_runtime_config: false,
}

export function getBootstrapPermissionHints(
  bootstrap: BootstrapResponse | null | undefined,
): BootstrapPermissionHints {
  return bootstrap?.permission_hints ?? EMPTY_BOOTSTRAP_PERMISSION_HINTS
}

export function isChatNavAvailable(hints: BootstrapPermissionHints): boolean {
  return hints.chat_available
}

export function canInviteFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_invite
}

export function canCreateActionFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_create_action
}

export function canCreateChecklistTemplateFromBootstrapHints(
  hints: BootstrapPermissionHints | null | undefined,
): boolean {
  return hints?.can_create_checklist_template === true
}

export function canManageRuntimeConfigFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_manage_runtime_config
}

export function canAccessManagementSpace(hints: BootstrapPermissionHints): boolean {
  return hints.can_manage_runtime_config || hints.can_invite
}
