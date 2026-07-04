import {
  canCreateActionPlanCatalogEntry,
  canDefineCrossPoleTasks,
} from './action-plan-management-access'

export type ActionPlanCreateMode = 'catalog' | 'execution'

export type ActionPlanCreateModeConfig = {
  canAccess: boolean
  showLibraryToggle: boolean
  showValidationToggle: boolean
  showAssigneeSheet: boolean
  showStaffSelfAssignee: boolean
  filterBusinessUnitsByScope: boolean
  canDefineCrossPoleTasks: boolean
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
  canCreateAction: boolean
  membershipId?: string
}): ActionPlanCreateModeConfig {
  const { mode, role, canCreateAction } = input
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
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    }
  }

  if (!canCreateAction) {
    return {
      canAccess: false,
      showLibraryToggle: false,
      showValidationToggle: false,
      showAssigneeSheet: false,
      showStaffSelfAssignee: false,
      filterBusinessUnitsByScope: shouldFilterBusinessUnitsByScope(role),
      canDefineCrossPoleTasks: false,
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
    defaultRequiresValidation: true,
    defaultSaveToLibrary: false,
  }
}
