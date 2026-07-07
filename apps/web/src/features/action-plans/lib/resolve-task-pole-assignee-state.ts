import type { ActionPlanTaskDraft } from './action-plan-form-validation'

type BusinessUnitOption = {
  id: string
  label: string
}

export type TaskPoleAssigneeState = {
  canPickAssignee: boolean
  poleLocked: boolean
  poleOptions: BusinessUnitOption[]
  requiresPoleChoice: boolean
  effectiveBusinessUnitId: string
}

function withLockedPoleOptionFallback(
  poleOptions: BusinessUnitOption[],
  businessUnitId: string,
  businessUnits: BusinessUnitOption[],
): BusinessUnitOption[] {
  if (poleOptions.some((unit) => unit.id === businessUnitId)) {
    return poleOptions
  }
  const knownLabel = businessUnits.find((unit) => unit.id === businessUnitId)?.label
  return [{ id: businessUnitId, label: knownLabel ?? "Pôle de l'assigné" }]
}

/** Owner/Director: assigneeBusinessUnitIds === [] (API admin convention). */
export function isAdminAssigneeTask(task: ActionPlanTaskDraft): boolean {
  return Boolean(task.assigneeMembershipId) && task.assigneeBusinessUnitIds.length === 0
}

export function shouldClearAssigneeOnPoleChange(
  task: ActionPlanTaskDraft,
  nextBusinessUnitId: string,
): boolean {
  if (!task.assigneeMembershipId) {
    return false
  }
  if (isAdminAssigneeTask(task)) {
    return false
  }
  if (task.assigneeBusinessUnitIds.length === 1) {
    return nextBusinessUnitId !== task.assigneeBusinessUnitIds[0]
  }
  return !task.assigneeBusinessUnitIds.includes(nextBusinessUnitId)
}

export function resolveTaskPoleAssigneeState(options: {
  task: ActionPlanTaskDraft
  pilotBusinessUnitId: string
  businessUnits: BusinessUnitOption[]
}): TaskPoleAssigneeState {
  const { task, pilotBusinessUnitId, businessUnits } = options
  const scopedAssigneeBusinessUnitIds = task.assigneeBusinessUnitIds

  if (task.assigneeMembershipId && scopedAssigneeBusinessUnitIds.length === 1) {
    const businessUnitId = scopedAssigneeBusinessUnitIds[0]
    const poleOptions = withLockedPoleOptionFallback(
      businessUnits.filter((unit) => unit.id === businessUnitId),
      businessUnitId,
      businessUnits,
    )
    return {
      canPickAssignee: true,
      poleLocked: true,
      poleOptions,
      requiresPoleChoice: false,
      effectiveBusinessUnitId: businessUnitId,
    }
  }

  if (task.assigneeMembershipId && scopedAssigneeBusinessUnitIds.length > 1) {
    const poleOptions = businessUnits.filter((unit) =>
      scopedAssigneeBusinessUnitIds.includes(unit.id),
    )
    return {
      canPickAssignee: true,
      poleLocked: false,
      poleOptions,
      requiresPoleChoice: !task.businessUnitId,
      effectiveBusinessUnitId: task.businessUnitId,
    }
  }

  if (isAdminAssigneeTask(task)) {
    return {
      canPickAssignee: true,
      poleLocked: false,
      poleOptions: businessUnits,
      requiresPoleChoice: !task.businessUnitId,
      effectiveBusinessUnitId: task.businessUnitId,
    }
  }

  return {
    canPickAssignee: true,
    poleLocked: false,
    poleOptions: businessUnits,
    requiresPoleChoice: false,
    effectiveBusinessUnitId: task.businessUnitId || pilotBusinessUnitId,
  }
}

export function applyAssigneeSelectionToTask(
  task: ActionPlanTaskDraft,
  selection: {
    membershipId: string
    displayName: string
    businessUnitIds: string[]
  },
): ActionPlanTaskDraft {
  const nextTask: ActionPlanTaskDraft = {
    ...task,
    assigneeMembershipId: selection.membershipId,
    assigneeDisplayName: selection.displayName,
    assigneeBusinessUnitIds: selection.businessUnitIds,
  }

  if (selection.businessUnitIds.length === 1) {
    return {
      ...nextTask,
      businessUnitId: selection.businessUnitIds[0],
    }
  }

  if (selection.businessUnitIds.length === 0) {
    return {
      ...nextTask,
      businessUnitId: '',
    }
  }

  if (
    nextTask.businessUnitId &&
    selection.businessUnitIds.length > 0 &&
    !selection.businessUnitIds.includes(nextTask.businessUnitId)
  ) {
    return {
      ...nextTask,
      businessUnitId: '',
    }
  }

  return nextTask
}
