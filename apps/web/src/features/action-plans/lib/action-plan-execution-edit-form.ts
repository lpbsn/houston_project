import type {
  ActionPlanExecutionDetail,
  ActionPlanTaskExecution,
  PatchedActionPlanExecutionUpdateRequest,
} from '../types'
import {
  createActionPlanEventPlanningDraft,
  splitIsoToDateAndTime,
  toSharedChronologyFields,
  type ActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'
import {
  actionPlanTaskFieldKey,
  isActionPlanTaskDraftActive,
} from './action-plan-field-errors'
import {
  createActionPlanAssigneeDraft,
  createActionPlanTaskDraft,
  type ActionPlanAssigneeDraft,
  type ActionPlanTaskDraft,
} from './action-plan-form-validation'
const MAX_TASKS = 10

export type ActionPlanExecutionEditFormValues = {
  title: string
  description: string
  pilotBusinessUnitId: string
  pilotBusinessUnitLabel: string
  requiresValidation: boolean
  useSharedChronology: boolean
  expectedUpdatedAt: string
  pendingTasks: ActionPlanTaskDraft[]
  knownPendingTaskIds: string[]
  treatedTasks: ActionPlanTaskExecution[]
  planningDraft: ActionPlanEventPlanningDraft
}

/** Flat field-error map (includes per-task keys `tasks.<id>.<field>`). */
export type ActionPlanExecutionEditFormErrors = Record<string, string>

export function isActionPlanExecutionTaskFrozen(
  task: Pick<ActionPlanTaskExecution, 'status'>,
): boolean {
  return task.status !== 'pending'
}

function toIsoDateTime(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  const parsed = Date.parse(trimmed)
  if (Number.isNaN(parsed)) {
    return null
  }
  return new Date(parsed).toISOString()
}

function hydrateAssignees(execution: ActionPlanExecutionDetail): ActionPlanAssigneeDraft[] {
  const drafts: ActionPlanAssigneeDraft[] = []
  const seen = new Set<string>()

  for (const group of execution.assignees_by_pole) {
    for (const assignee of group.assignees) {
      if (seen.has(assignee.membership_id)) {
        continue
      }
      seen.add(assignee.membership_id)
      drafts.push(
        createActionPlanAssigneeDraft({
          membershipId: assignee.membership_id,
          businessUnitId: group.business_unit.id,
          displayName: assignee.display_name,
          startAt: assignee.start_at ?? '',
          endAt: assignee.end_at ?? '',
          visibleFrom: assignee.visible_from ?? '',
        }),
      )
    }
  }

  return drafts
}

function actionPlanTaskExecutionToDraft(task: ActionPlanTaskExecution): ActionPlanTaskDraft {
  return {
    ...createActionPlanTaskDraft(task.business_unit.id),
    id: task.id,
    task: task.task,
    description: task.description ?? '',
    businessUnitId: task.business_unit.id,
    deadlineAt: task.deadline_at ?? '',
    assigneeMembershipId: task.assigned_membership_id ?? '',
    assigneeDisplayName: task.assigned_display_name ?? '',
    assigneeBusinessUnitIds: [task.business_unit.id],
  }
}

export function hydrateActionPlanExecutionEditForm(
  execution: ActionPlanExecutionDetail,
): ActionPlanExecutionEditFormValues {
  const pendingTasks = execution.task_executions
    .filter((task) => task.status === 'pending')
    .slice()
    .sort((left, right) => left.position - right.position)
    .map(actionPlanTaskExecutionToDraft)

  const treatedTasks = execution.task_executions
    .filter((task) => isActionPlanExecutionTaskFrozen(task))
    .slice()
    .sort((left, right) => left.position - right.position)

  const assignees = hydrateAssignees(execution)
  const planningDraft = createActionPlanEventPlanningDraft()
  planningDraft.assignees = assignees
  planningDraft.usePerAssigneeChronology = !execution.use_shared_chronology
  planningDraft.repeatEnabled = false

  if (execution.use_shared_chronology) {
    const start = splitIsoToDateAndTime(execution.start_at ?? '')
    const end = splitIsoToDateAndTime(execution.end_at ?? '')
    planningDraft.startDate = start.date
    planningDraft.startTime = start.time
    planningDraft.endDate = end.date
    planningDraft.endTime = end.time
  }

  return {
    title: execution.title,
    description: execution.description ?? '',
    pilotBusinessUnitId: execution.pilot_business_unit.id,
    pilotBusinessUnitLabel: execution.pilot_business_unit.specific_name,
    requiresValidation: execution.requires_validation,
    useSharedChronology: execution.use_shared_chronology,
    expectedUpdatedAt: execution.updated_at,
    pendingTasks,
    knownPendingTaskIds: pendingTasks.map((task) => task.id),
    treatedTasks,
    planningDraft,
  }
}

function isRetainedPendingTask(
  task: ActionPlanTaskDraft,
  knownPendingTaskIds: ReadonlySet<string>,
): boolean {
  // Known pending rows stay in the authoritative PATCH list even with an empty title
  // so clearing the title cannot silently omit → delete them. Blank new draft rows
  // (not yet known) remain droppable placeholders.
  return knownPendingTaskIds.has(task.id) || Boolean(task.task.trim())
}

export function listExecutionPendingPayloadTaskIds(
  pendingTasks: ActionPlanTaskDraft[],
  knownPendingTaskIds: ReadonlySet<string> | readonly string[],
): string[] {
  const known = knownPendingTaskIds instanceof Set
    ? knownPendingTaskIds
    : new Set(knownPendingTaskIds)
  return pendingTasks
    .filter((task) => isRetainedPendingTask(task, known))
    .map((task) => task.id)
}

export function validateActionPlanExecutionEditForm(
  values: Pick<
    ActionPlanExecutionEditFormValues,
    | 'title'
    | 'pendingTasks'
    | 'treatedTasks'
    | 'pilotBusinessUnitId'
    | 'planningDraft'
    | 'useSharedChronology'
    | 'knownPendingTaskIds'
  >,
  options: {
    canDefineCrossPoleTasks: boolean
    staffMode: boolean
    membershipId?: string
  },
): ActionPlanExecutionEditFormErrors {
  const errors: ActionPlanExecutionEditFormErrors = {}

  if (!values.title.trim()) {
    errors.title = 'Le titre est obligatoire.'
  }

  const knownPendingTaskIds = new Set(values.knownPendingTaskIds)
  const retainedTasks = values.pendingTasks.filter((task) =>
    isRetainedPendingTask(task, knownPendingTaskIds),
  )

  const totalTasks = retainedTasks.length + values.treatedTasks.length
  if (totalTasks > MAX_TASKS) {
    errors.tasks = `Maximum ${MAX_TASKS} tâches.`
  }

  for (const task of retainedTasks) {
    if (!task.task.trim()) {
      errors[actionPlanTaskFieldKey(task.id, 'task')] =
        'Chaque tâche conservée doit avoir un titre.'
      continue
    }

    if (
      task.assigneeMembershipId &&
      !task.businessUnitId &&
      task.assigneeBusinessUnitIds.length > 1
    ) {
      errors[actionPlanTaskFieldKey(task.id, 'businessUnitId')] =
        'Choisissez le pôle de l’assigné pour chaque tâche concernée.'
    }

    const effectiveBusinessUnitId = task.businessUnitId || values.pilotBusinessUnitId
    if (!effectiveBusinessUnitId) {
      errors[actionPlanTaskFieldKey(task.id, 'businessUnitId')] =
        'Chaque tâche doit avoir un pôle d’activité ou un pôle pilote.'
    } else if (
      !options.canDefineCrossPoleTasks &&
      values.pilotBusinessUnitId &&
      effectiveBusinessUnitId !== values.pilotBusinessUnitId
    ) {
      errors[actionPlanTaskFieldKey(task.id, 'businessUnitId')] =
        'Les tâches hors pôle pilote sont réservées aux administrateurs.'
    } else if (
      options.staffMode &&
      effectiveBusinessUnitId !== values.pilotBusinessUnitId
    ) {
      errors[actionPlanTaskFieldKey(task.id, 'businessUnitId')] =
        'Les tâches staff doivent rester sur le pôle pilote.'
    }
  }

  // Active non-retained drafts (e.g. new row with description only) must also be blocked.
  for (const task of values.pendingTasks) {
    if (knownPendingTaskIds.has(task.id) || task.task.trim()) {
      continue
    }
    if (!isActionPlanTaskDraftActive(task)) {
      continue
    }
    errors[actionPlanTaskFieldKey(task.id, 'task')] = 'Chaque tâche doit avoir un titre.'
  }

  const validAssignees = values.planningDraft.assignees.filter(
    (assignee) => assignee.membershipId && assignee.businessUnitId,
  )
  if (validAssignees.length === 0) {
    errors.assignees = 'Au moins un assigné est requis.'
  }

  if (options.staffMode) {
    if (!options.membershipId) {
      errors.assignees = 'Le staff ne peut s’assigner qu’à lui-même.'
    } else if (
      validAssignees.length !== 1 ||
      validAssignees[0]?.membershipId !== options.membershipId ||
      validAssignees[0]?.businessUnitId !== values.pilotBusinessUnitId
    ) {
      errors.assignees = 'Le staff ne peut s’assigner qu’à lui-même.'
    }
  }

  if (values.useSharedChronology) {
    const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(values.planningDraft)
    if (sharedEndAt && sharedStartAt) {
      if (Date.parse(sharedEndAt) <= Date.parse(sharedStartAt)) {
        errors.endAt = 'La fin doit être après le début.'
      }
    } else if (sharedEndAt && !sharedStartAt) {
      errors.endAt = 'Une date de fin nécessite une date de début.'
    }
  } else {
    for (const assignee of validAssignees) {
      if (!assignee.endAt.trim()) {
        continue
      }
      if (assignee.startAt.trim() && Date.parse(assignee.endAt) <= Date.parse(assignee.startAt)) {
        errors.endAt = 'La fin doit être après le début.'
        break
      }
    }
  }

  return errors
}

export function hasActionPlanExecutionEditFormErrors(
  errors: ActionPlanExecutionEditFormErrors,
): boolean {
  return Object.keys(errors).length > 0
}

function resolvePendingTaskPositions(treatedTasks: ActionPlanTaskExecution[]): number[] {
  const reserved = new Set(treatedTasks.map((task) => task.position))
  const free: number[] = []
  for (let position = 1; position <= MAX_TASKS; position += 1) {
    if (!reserved.has(position)) {
      free.push(position)
    }
  }
  return free
}

export function buildActionPlanExecutionUpdateRequest(
  values: ActionPlanExecutionEditFormValues,
): PatchedActionPlanExecutionUpdateRequest {
  const knownPendingIds = new Set(values.knownPendingTaskIds)
  const freePositions = resolvePendingTaskPositions(values.treatedTasks)
  const pendingTasks = values.pendingTasks
    .filter((task) => isRetainedPendingTask(task, knownPendingIds))
    .map((task, index) => ({
      ...(knownPendingIds.has(task.id) ? { id: task.id } : {}),
      task: task.task.trim(),
      description: task.description.trim(),
      business_unit_id: task.businessUnitId || values.pilotBusinessUnitId,
      position: freePositions[index] ?? index + 1,
      deadline_at: task.deadlineAt ? toIsoDateTime(task.deadlineAt) : null,
      assigned_membership_id: task.assigneeMembershipId || null,
    }))

  const assignees = values.planningDraft.assignees
    .filter((assignee) => assignee.membershipId && assignee.businessUnitId)
    .map((assignee) => {
      const endAt = values.useSharedChronology
        ? toSharedChronologyFields(values.planningDraft).sharedEndAt
        : assignee.endAt
      return {
        membership_id: assignee.membershipId,
        business_unit_id: assignee.businessUnitId,
        end_at: endAt ? toIsoDateTime(endAt) : null,
      }
    })

  const body: PatchedActionPlanExecutionUpdateRequest = {
    expected_updated_at: values.expectedUpdatedAt,
    title: values.title.trim(),
    description: values.description.trim(),
    requires_validation: values.requiresValidation,
    assignees,
    pending_tasks: pendingTasks,
  }

  if (values.useSharedChronology) {
    const { sharedEndAt } = toSharedChronologyFields(values.planningDraft)
    body.end_at = sharedEndAt ? toIsoDateTime(sharedEndAt) : null
  }

  return body
}

export function isActionPlanExecutionEditConflictError(error: {
  status?: number
  code?: string | null
}): boolean {
  if (error.status === 409 || error.code === 'stale_execution') {
    return true
  }
  return error.code === 'invalid_action_plan_state'
}
