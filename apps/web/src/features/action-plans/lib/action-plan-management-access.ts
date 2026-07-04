export function canAccessActionPlanCatalog(options: {
  establishmentId: string | null | undefined
  activeMembershipId: string | null | undefined
  role: string | null | undefined
}): boolean {
  if (!options.establishmentId || !options.activeMembershipId) {
    return false
  }
  return options.role === 'manager' || options.role === 'director' || options.role === 'owner'
}

export function canCreateActionPlanCatalogEntry(role: string | null | undefined): boolean {
  return role === 'manager' || role === 'director' || role === 'owner'
}

export function canDefineCrossPoleTasks(role: string | null | undefined): boolean {
  return role === 'director' || role === 'owner'
}

export function canCreateExecutionFeedActionPlan(canCreateAction: boolean): boolean {
  return canCreateAction === true
}

/** Bootstrap/role gate for creating an action plan linked to a signal. Staff denied (§26.13). */
export function canCreateSignalLinkedActionPlan(options: {
  role: string | null | undefined
  canCreateAction: boolean
}): boolean {
  if (options.canCreateAction !== true) {
    return false
  }
  return canCreateActionPlanCatalogEntry(options.role)
}

import { shouldShowSignalCreateActionPlan } from '@/features/signals/lib/signal-create-action'

/** Signal-scoped hint gate — same contract as the signal detail CTA. */
export function canCreateSignalLinkedActionPlanFromSignalHints(
  hints: { can_create_action?: boolean } | null | undefined,
): boolean {
  return shouldShowSignalCreateActionPlan(hints)
}
