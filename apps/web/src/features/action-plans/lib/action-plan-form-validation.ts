import type { ActionPlanScheduleDraft } from './action-plan-schedule-form'
import { isActionPlanScheduleConfigured } from './action-plan-schedule-form'
import {
  validateActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'
import type { ActionPlanTaskTemplate } from '../types'

export type ActionPlanTaskDraft = {
  id: string
  task: string
  description: string
  businessUnitId: string
  deadlineAt: string
  assigneeMembershipId: string
  assigneeDisplayName: string
  assigneeBusinessUnitIds: string[]
}

export function createActionPlanTaskDraft(businessUnitId = ''): ActionPlanTaskDraft {
  return {
    id: crypto.randomUUID(),
    task: '',
    description: '',
    businessUnitId,
    deadlineAt: '',
    assigneeMembershipId: '',
    assigneeDisplayName: '',
    assigneeBusinessUnitIds: [],
  }
}

export function actionPlanTaskTemplateToDraft(task: ActionPlanTaskTemplate): ActionPlanTaskDraft {
  return {
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

export type ActionPlanAssigneeDraft = {
  id: string
  membershipId: string
  businessUnitId: string
  displayName: string
  startAt: string
  endAt: string
  visibleFrom: string
}

export function createActionPlanAssigneeDraft(
  partial: Partial<ActionPlanAssigneeDraft> = {},
): ActionPlanAssigneeDraft {
  return {
    id: partial.id ?? crypto.randomUUID(),
    membershipId: partial.membershipId ?? '',
    businessUnitId: partial.businessUnitId ?? '',
    displayName: partial.displayName ?? '',
    startAt: partial.startAt ?? '',
    endAt: partial.endAt ?? '',
    visibleFrom: partial.visibleFrom ?? '',
  }
}

export type ActionPlanCreateFormValues = {
  title: string
  description: string
  pilotBusinessUnitId: string
  requiresValidation: boolean
  saveToLibrary: boolean
  useSharedChronology: boolean
  sharedStartAt: string
  sharedEndAt: string
  sharedVisibleFrom: string
  tasks: ActionPlanTaskDraft[]
  assignees: ActionPlanAssigneeDraft[]
  schedule: ActionPlanScheduleDraft
  sourceSignalId?: string | null
}

export type ActionPlanCreateFormErrors = Partial<
  Record<
    | 'title'
    | 'pilotBusinessUnitId'
    | 'tasks'
    | 'assignees'
    | 'sharedStartAt'
    | 'sharedEndAt'
    | 'recurrenceDays'
    | 'recurrenceEndDate'
    | 'endDate'
    | 'startAt'
    | 'startTime'
    | 'endTime'
    | 'submit',
    string
  >
>

const MAX_TASKS = 10

export function validateActionPlanCreateForm(
  values: ActionPlanCreateFormValues,
  options: {
    canDefineCrossPoleTasks: boolean
    staffExecutionMode?: { membershipId: string; pilotBusinessUnitId: string }
  },
): ActionPlanCreateFormErrors {
  const errors: ActionPlanCreateFormErrors = {}

  if (!values.title.trim()) {
    errors.title = 'Le titre est obligatoire.'
  }

  if (!values.pilotBusinessUnitId) {
    errors.pilotBusinessUnitId = 'Sélectionnez un pôle d’activité pilote.'
  }

  const nonEmptyTasks = values.tasks.filter((task) => task.task.trim())
  if (nonEmptyTasks.length > MAX_TASKS) {
    errors.tasks = `Maximum ${MAX_TASKS} tâches.`
  }

  for (const task of nonEmptyTasks) {
    if (
      task.assigneeMembershipId &&
      !task.businessUnitId &&
      task.assigneeBusinessUnitIds.length > 1
    ) {
      errors.tasks = 'Choisissez le pôle de l’assigné pour chaque tâche concernée.'
      break
    }
    if (
      task.assigneeMembershipId &&
      task.assigneeBusinessUnitIds.length === 0 &&
      !task.businessUnitId
    ) {
      errors.tasks =
        'Sélectionnez un pôle d’activité pour chaque tâche assignée à un Owner ou un Director.'
      break
    }
    const effectiveBusinessUnitId = task.businessUnitId || values.pilotBusinessUnitId
    if (!effectiveBusinessUnitId) {
      errors.tasks = 'Chaque tâche doit avoir un pôle d’activité ou un pôle pilote.'
      break
    }
    if (
      !options.canDefineCrossPoleTasks &&
      values.pilotBusinessUnitId &&
      effectiveBusinessUnitId !== values.pilotBusinessUnitId
    ) {
      errors.tasks = 'Les tâches hors pôle pilote sont réservées aux administrateurs.'
      break
    }
  }

  if (!values.saveToLibrary && !isActionPlanScheduleConfigured(values.schedule)) {
    for (const assignee of values.assignees.filter((item) => item.membershipId)) {
      if (!assignee.businessUnitId) {
        errors.assignees = 'Chaque assigné doit être rattaché à un pôle.'
        break
      }
    }
  }

  if (options.staffExecutionMode) {
    const { membershipId, pilotBusinessUnitId } = options.staffExecutionMode

    if (values.saveToLibrary) {
      errors.submit = 'Les plans staff ne peuvent pas être enregistrés dans la bibliothèque.'
    }
    if (values.requiresValidation) {
      errors.submit = 'Les plans staff ne peuvent pas exiger une validation.'
    }
    if (isActionPlanScheduleConfigured(values.schedule)) {
      errors.submit = 'Le staff ne peut pas planifier un plan à la création.'
    }

    const validAssignees = values.assignees.filter((assignee) => assignee.membershipId)
    if (validAssignees.length !== 1) {
      errors.assignees = 'Le staff ne peut s’assigner qu’à lui-même.'
    } else {
      const assignee = validAssignees[0]
      if (assignee.membershipId !== membershipId) {
        errors.assignees = 'Le staff ne peut s’assigner qu’à lui-même.'
      }
      if (assignee.businessUnitId !== pilotBusinessUnitId) {
        errors.assignees = 'L’assigné staff doit être sur le pôle pilote.'
      }
    }

    for (const task of nonEmptyTasks) {
      const effectiveBusinessUnitId = task.businessUnitId || pilotBusinessUnitId
      if (effectiveBusinessUnitId !== pilotBusinessUnitId) {
        errors.tasks = 'Les tâches staff doivent rester sur le pôle pilote.'
        break
      }
    }
  }

  return errors
}

export function validateActionPlanCreatePlanningErrors(
  planningDraft: ActionPlanEventPlanningDraft,
  options: {
    saveToLibrary: boolean
    staffExecutionMode?: { membershipId: string; pilotBusinessUnitId: string }
  },
): Record<string, string> {
  return validateActionPlanEventPlanningDraft(planningDraft, {
    requireAssignees: !options.saveToLibrary || planningDraft.repeatEnabled,
    allowRepeat: !options.staffExecutionMode,
  })
}

export function hasActionPlanCreateFormErrors(errors: ActionPlanCreateFormErrors): boolean {
  return Object.keys(errors).length > 0
}
