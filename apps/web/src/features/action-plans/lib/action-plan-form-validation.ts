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

  if (options.staffExecutionMode) {
    const { membershipId, pilotBusinessUnitId } = options.staffExecutionMode

    if (values.saveToLibrary) {
      errors.submit = 'Les plans staff ne peuvent pas être enregistrés dans la bibliothèque.'
    }
    if (values.requiresValidation) {
      errors.submit = 'Les plans staff ne peuvent pas exiger une validation.'
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
      if (task.businessUnitId !== pilotBusinessUnitId) {
        errors.tasks = 'Les tâches staff doivent rester sur le pôle pilote.'
        break
      }
    }
  }

  return errors
}

export function hasActionPlanCreateFormErrors(errors: ActionPlanCreateFormErrors): boolean {
  return Object.keys(errors).length > 0
}
