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
