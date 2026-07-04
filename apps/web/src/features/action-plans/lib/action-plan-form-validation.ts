export type ActionPlanTaskDraft = {
  id: string
  task: string
  businessUnitId: string
}

export function createActionPlanTaskDraft(businessUnitId = ''): ActionPlanTaskDraft {
  return { id: crypto.randomUUID(), task: '', businessUnitId }
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
}

export type ActionPlanCreateFormErrors = Partial<
  Record<
    | 'title'
    | 'pilotBusinessUnitId'
    | 'tasks'
    | 'assignees'
    | 'sharedStartAt'
    | 'sharedEndAt'
    | 'submit',
    string
  >
>

const MAX_TASKS = 10

export function validateActionPlanCreateForm(
  values: ActionPlanCreateFormValues,
  options: { canDefineCrossPoleTasks: boolean },
): ActionPlanCreateFormErrors {
  const errors: ActionPlanCreateFormErrors = {}

  if (!values.title.trim()) {
    errors.title = 'Le titre est obligatoire.'
  }

  if (!values.pilotBusinessUnitId) {
    errors.pilotBusinessUnitId = 'Sélectionnez un pôle d’activité pilote.'
  }

  const nonEmptyTasks = values.tasks.filter((task) => task.task.trim())
  if (nonEmptyTasks.length === 0) {
    errors.tasks = 'Ajoutez au moins une tâche.'
  }
  if (nonEmptyTasks.length > MAX_TASKS) {
    errors.tasks = `Maximum ${MAX_TASKS} tâches.`
  }

  for (const task of nonEmptyTasks) {
    if (!task.businessUnitId) {
      errors.tasks = 'Chaque tâche doit avoir un pôle d’activité.'
      break
    }
    if (
      !options.canDefineCrossPoleTasks &&
      values.pilotBusinessUnitId &&
      task.businessUnitId !== values.pilotBusinessUnitId
    ) {
      errors.tasks = 'Les tâches hors pôle pilote sont réservées aux administrateurs.'
      break
    }
  }

  if (!values.saveToLibrary) {
    const validAssignees = values.assignees.filter((assignee) => assignee.membershipId)
    if (validAssignees.length === 0) {
      errors.assignees = 'Ajoutez au moins un assigné pour lancer le plan.'
    }
    for (const assignee of validAssignees) {
      if (!assignee.businessUnitId) {
        errors.assignees = 'Chaque assigné doit être rattaché à un pôle.'
        break
      }
    }
    if (values.useSharedChronology && values.sharedEndAt && values.sharedStartAt) {
      if (Date.parse(values.sharedEndAt) <= Date.parse(values.sharedStartAt)) {
        errors.sharedEndAt = 'La fin doit être postérieure au début.'
      }
    }
  }

  return errors
}

export function hasActionPlanCreateFormErrors(errors: ActionPlanCreateFormErrors): boolean {
  return Object.keys(errors).length > 0
}
