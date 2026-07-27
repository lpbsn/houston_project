import {
  canCreateActionPlanCatalogEntryFromHints,
  canCreateSignalLinkedActionPlan,
  canDefineCrossPoleTasks,
  canManageActionPlanCatalog,
} from './action-plan-management-access'

export type ActionPlanCreateMode = 'catalog' | 'execution' | 'signal-linked' | 'template-edit'

export type ActionPlanCreateModeConfig = {
  canAccess: boolean
  showLibraryToggle: boolean
  showValidationToggle: boolean
  showAssigneeSheet: boolean
  showStaffSelfAssignee: boolean
  showScheduleSection: boolean
  filterBusinessUnitsByScope: boolean
  canDefineCrossPoleTasks: boolean
  lockPilotBusinessUnit: boolean
  defaultRequiresValidation: boolean
  defaultSaveToLibrary: boolean
}

function isStaffRole(role: string | null): boolean {
  return role === 'staff'
}

function shouldFilterBusinessUnitsByScope(role: string | null): boolean {
  return role === 'manager' || role === 'staff'
}

function resolveStaffCreateOptions(): ActionPlanCreateModeConfig {
  return {
    canAccess: true,
    showLibraryToggle: false,
    showValidationToggle: false,
    showAssigneeSheet: false,
    showStaffSelfAssignee: true,
    showScheduleSection: false,
    filterBusinessUnitsByScope: true,
    canDefineCrossPoleTasks: false,
    lockPilotBusinessUnit: false,
    defaultRequiresValidation: false,
    defaultSaveToLibrary: false,
  }
}

function resolveManagementCreateOptions(role: string | null): ActionPlanCreateModeConfig {
  const canCrossPole = canDefineCrossPoleTasks(role)
  return {
    canAccess: true,
    showLibraryToggle: true,
    showValidationToggle: true,
    showAssigneeSheet: true,
    showStaffSelfAssignee: false,
    showScheduleSection: true,
    filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
    canDefineCrossPoleTasks: canCrossPole,
    lockPilotBusinessUnit: false,
    defaultRequiresValidation: true,
    defaultSaveToLibrary: false,
  }
}

function resolveDeniedCreateOptions(role: string | null): ActionPlanCreateModeConfig {
  return {
    canAccess: false,
    showLibraryToggle: false,
    showValidationToggle: false,
    showAssigneeSheet: false,
    showStaffSelfAssignee: false,
    showScheduleSection: false,
    filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
    canDefineCrossPoleTasks: false,
    lockPilotBusinessUnit: false,
    defaultRequiresValidation: true,
    defaultSaveToLibrary: false,
  }
}

export function resolveActionPlanCreateModeConfig(input: {
  mode: ActionPlanCreateMode
  role: string | null
  canCreateActionPlan: boolean
  canCreateCatalogActionPlan?: boolean
  membershipId?: string
  /** When set for signal-linked: lock pilot only if the signal already has a responsible pole. */
  signalHasResponsibleBusinessUnit?: boolean
}): ActionPlanCreateModeConfig {
  const { mode, role, canCreateActionPlan } = input
  const isStaff = isStaffRole(role)
  const canCrossPole = canDefineCrossPoleTasks(role)

  if (mode === 'signal-linked') {
    const lockPilot =
      input.signalHasResponsibleBusinessUnit === undefined
        ? true
        : input.signalHasResponsibleBusinessUnit
    return {
      canAccess: canCreateSignalLinkedActionPlan({ role, canCreateActionPlan }),
      showLibraryToggle: false,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      showScheduleSection: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: canCrossPole,
      lockPilotBusinessUnit: lockPilot,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (mode === 'template-edit') {
    return {
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: true,
      showAssigneeSheet: false,
      showStaffSelfAssignee: false,
      showScheduleSection: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: canCrossPole,
      lockPilotBusinessUnit: true,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (mode === 'catalog') {
    if (!canCreateActionPlanCatalogEntryFromHints(input.canCreateCatalogActionPlan)) {
      return resolveDeniedCreateOptions(role)
    }
    return resolveManagementCreateOptions(role)
  }

  if (!canCreateActionPlan) {
    return resolveDeniedCreateOptions(role)
  }

  if (isStaff) {
    return resolveStaffCreateOptions()
  }

  if (canManageActionPlanCatalog(role)) {
    return resolveManagementCreateOptions(role)
  }

  return resolveDeniedCreateOptions(role)
}
