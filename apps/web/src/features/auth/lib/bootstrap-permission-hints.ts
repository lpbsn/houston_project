import type { BootstrapResponse } from '@/features/auth/types'

export type BootstrapPermissionHints = BootstrapResponse['permission_hints']

const EMPTY_BOOTSTRAP_PERMISSION_HINTS: BootstrapPermissionHints = {
  chat_available: false,
  can_create_action_plan: false,
  can_create_catalog_action_plan: false,
  can_view_action_plan_catalog: false,
  can_invite: false,
  can_manage_runtime_config: false,
  can_view_team: false,
  can_manage_organization: false,
  can_create_establishment: false,
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

export function canCreateActionPlanFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_create_action_plan
}

export function canCreateCatalogActionPlanFromBootstrapHints(
  hints: BootstrapPermissionHints | null | undefined,
): boolean {
  return hints?.can_create_catalog_action_plan === true
}

export function canViewActionPlanCatalogFromBootstrapHints(
  hints: BootstrapPermissionHints | null | undefined,
): boolean {
  return hints?.can_view_action_plan_catalog === true
}

export function canManageRuntimeConfigFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_manage_runtime_config
}

export function canViewTeamFromBootstrapHints(hints: BootstrapPermissionHints): boolean {
  return hints.can_view_team
}

export function canCreateEstablishmentFromBootstrapHints(
  hints: BootstrapPermissionHints,
): boolean {
  return hints.can_create_establishment === true
}

export function canManageOrganizationFromBootstrapHints(
  hints: BootstrapPermissionHints,
): boolean {
  return hints.can_manage_organization === true
}

export function canAccessManagementSpace(hints: BootstrapPermissionHints): boolean {
  return hints.can_manage_runtime_config || hints.can_invite
}
