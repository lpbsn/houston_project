import { shouldShowSignalCreateActionPlan } from '@/features/signals/lib/signal-create-action'

export function canAccessActionPlanCatalog(options: {
  establishmentId: string | null | undefined
  activeMembershipId: string | null | undefined
  role: string | null | undefined
  canViewActionPlanCatalog?: boolean
}): boolean {
  if (!options.establishmentId || !options.activeMembershipId) {
    return false
  }
  if (options.canViewActionPlanCatalog === true) {
    return true
  }
  if (options.canViewActionPlanCatalog === false) {
    return false
  }
  return options.role === 'manager' || options.role === 'director' || options.role === 'owner'
}

export function canManageActionPlanCatalog(role: string | null | undefined): boolean {
  return role === 'manager' || role === 'director' || role === 'owner'
}

export function canCreateActionPlanCatalogEntryFromHints(
  canCreateCatalogActionPlan?: boolean,
): boolean {
  return canCreateCatalogActionPlan === true
}

export function canCreateActionPlanCatalogEntry(role: string | null | undefined): boolean {
  return canManageActionPlanCatalog(role)
}

export function canDefineCrossPoleTasks(role: string | null | undefined): boolean {
  return role === 'director' || role === 'owner'
}

export function canCreateExecutionFeedActionPlan(canCreateActionPlan: boolean): boolean {
  return canCreateActionPlan === true
}

/** Bootstrap/role gate for creating an action plan linked to a signal. Staff denied (§26.13). */
export function canCreateSignalLinkedActionPlan(options: {
  role: string | null | undefined
  canCreateActionPlan: boolean
}): boolean {
  if (options.canCreateActionPlan !== true) {
    return false
  }
  return canCreateActionPlanCatalogEntry(options.role)
}

/** Signal-scoped hint gate — same contract as the signal detail CTA. */
export function canCreateSignalLinkedActionPlanFromSignalHints(
  hints: { can_create_linked_action_plan?: boolean } | null | undefined,
): boolean {
  return shouldShowSignalCreateActionPlan(hints)
}

export function isStaffActionPlanUsageRole(role: string | null | undefined): boolean {
  return role === 'staff'
}
