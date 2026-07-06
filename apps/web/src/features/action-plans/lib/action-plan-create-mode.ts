import {
  canCreateActionPlanCatalogEntry,
  canCreateSignalLinkedActionPlan,
  canDefineCrossPoleTasks,
} from './action-plan-management-access'

export type ActionPlanCreateMode = 'catalog' | 'execution' | 'signal-linked'

export type ActionPlanCreateModeConfig = {
  canAccess: boolean
  showLibraryToggle: boolean
  showValidationToggle: boolean
  showAssigneeSheet: boolean
  showStaffSelfAssignee: boolean
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

export function resolveActionPlanCreateModeConfig(input: {
  mode: ActionPlanCreateMode
  role: string | null
  canCreateActionPlan: boolean
  membershipId?: string
}): ActionPlanCreateModeConfig {
  const { mode, role, canCreateActionPlan } = input
  const isStaff = isStaffRole(role)
  const canCrossPole = canDefineCrossPoleTasks(role)

  if (mode === 'catalog') {
    return {
      canAccess: canCreateActionPlanCatalogEntry(role),
      showLibraryToggle: true,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: canCrossPole,
      lockPilotBusinessUnit: false,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (mode === 'signal-linked') {
    return {
      canAccess: canCreateSignalLinkedActionPlan({ role, canCreateActionPlan }),
      showLibraryToggle: false,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: canCrossPole,
      lockPilotBusinessUnit: true,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (!canCreateActionPlan) {
    return {
      canAccess: false,
      showLibraryToggle: false,
      showValidationToggle: false,
      showAssigneeSheet: false,
      showStaffSelfAssignee: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: false,
      lockPilotBusinessUnit: false,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (isStaff) {
    return {
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: false,
      showAssigneeSheet: false,
      showStaffSelfAssignee: true,
      filterBusinessUnitsByScope: true,
      canDefineCrossPoleTasks: false,
      lockPilotBusinessUnit: false,
      defaultRequiresValidation: false,
      defaultSaveToLibrary: false,
    }
  }

  return {
    canAccess: true,
    showLibraryToggle: false,
    showValidationToggle: true,
    showAssigneeSheet: true,
    showStaffSelfAssignee: false,
    filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
    canDefineCrossPoleTasks: canCrossPole,
    lockPilotBusinessUnit: false,
    defaultRequiresValidation: true,
    defaultSaveToLibrary: false,
  }
}
