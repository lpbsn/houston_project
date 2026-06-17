import type { AssignmentFormValues } from '@/features/checklists/lib/checklist-assignment-create-payload'

export type { AssignmentFormValues }

export type AssignmentFormErrors = Partial<
  Record<
    'assignedTo' | 'startDate' | 'endDate' | 'startAt' | 'endAt' | 'recurrenceDays',
    string
  >
>

export type TemplateScheduleFormErrors = Partial<
  Record<
    'assignedTo' | 'startAt' | 'endAt' | 'recurrenceDays' | 'recurrenceEndDate' | 'submit',
    string
  >
>

export function validateTemplateScheduleForm(
  values: {
    assignedTo: string
    startAt: string
    endAt: string
    recurrenceDays: string[]
    recurrenceEndDate: string
    canLaunchExecution: boolean
    canCreateAssignment: boolean
  },
  options?: { referenceDateIso?: string },
): TemplateScheduleFormErrors {
  const errors: TemplateScheduleFormErrors = {}
  const isRecurring = values.recurrenceDays.length > 0

  if (!values.assignedTo.trim()) {
    errors.assignedTo = 'Sélectionnez un membre assigné.'
  }

  if (!values.startAt.trim()) {
    errors.startAt = 'L’heure de début est obligatoire.'
  }

  if (!values.endAt.trim()) {
    errors.endAt = 'L’heure de fin est obligatoire.'
  }

  if (values.startAt && values.endAt && values.endAt <= values.startAt) {
    errors.endAt = 'L’heure de fin doit être postérieure à l’heure de début.'
  }

  if (isRecurring) {
    if (!values.canCreateAssignment) {
      errors.submit = 'Vous ne pouvez pas créer une affectation récurrente.'
    }
    if (!values.recurrenceEndDate.trim()) {
      errors.recurrenceEndDate = 'La fin de la récurrence est obligatoire.'
    } else if (
      options?.referenceDateIso &&
      values.recurrenceEndDate < options.referenceDateIso
    ) {
      errors.recurrenceEndDate = 'La fin de la récurrence ne peut pas être dans le passé.'
    }
  } else if (!values.canLaunchExecution) {
    errors.submit = 'Vous ne pouvez pas lancer une exécution ponctuelle.'
  }

  const uniqueDays = new Set(values.recurrenceDays)
  if (uniqueDays.size !== values.recurrenceDays.length) {
    errors.recurrenceDays = 'Chaque jour ne peut être sélectionné qu’une fois.'
  }

  return errors
}

export function hasTemplateScheduleFormErrors(errors: TemplateScheduleFormErrors): boolean {
  return Object.keys(errors).length > 0
}

export function validateAssignmentForm(values: AssignmentFormValues): AssignmentFormErrors {
  const errors: AssignmentFormErrors = {}

  if (!values.assignedTo.trim()) {
    errors.assignedTo = 'Sélectionnez un membre assigné.'
  }

  if (!values.startDate.trim()) {
    errors.startDate = 'La date de début est obligatoire.'
  }

  if (!values.endDate.trim() && values.recurrenceDays.length > 0) {
    errors.endDate = 'La date de fin est obligatoire pour une affectation récurrente.'
  }

  if (!values.startAt.trim()) {
    errors.startAt = 'L’heure de début est obligatoire.'
  }

  if (!values.endAt.trim()) {
    errors.endAt = 'L’heure de fin est obligatoire.'
  }

  if (values.startDate && values.endDate && values.endDate < values.startDate) {
    errors.endDate = 'La date de fin doit être postérieure ou égale à la date de début.'
  }

  if (values.startAt && values.endAt && values.endAt <= values.startAt) {
    errors.endAt = 'L’heure de fin doit être postérieure à l’heure de début (même jour).'
  }

  const uniqueDays = new Set(values.recurrenceDays)
  if (uniqueDays.size !== values.recurrenceDays.length) {
    errors.recurrenceDays = 'Chaque jour ne peut être sélectionné qu’une fois.'
  }

  return errors
}

export function hasAssignmentFormErrors(errors: AssignmentFormErrors): boolean {
  return Object.keys(errors).length > 0
}

export function validateRegisteredTemplateCreate(values: {
  title: string
  businessUnitId: string
  taskCount: number
  assignNow: boolean
  assignedTo: string
}): string | null {
  if (!values.title.trim()) {
    return 'Le titre est obligatoire.'
  }
  if (!values.businessUnitId.trim()) {
    return 'Le pôle est obligatoire.'
  }
  if (values.taskCount === 0) {
    return 'Ajoutez au moins une tâche.'
  }
  if (values.assignNow && !values.assignedTo.trim()) {
    return 'Sélectionnez un membre assigné.'
  }
  return null
}

export function validateTask(task: string): string | null {
  if (!task.trim()) {
    return 'La tâche est obligatoire.'
  }
  return null
}

export type ChecklistCreateValidationResult =
  | { ok: true }
  | {
      ok: false
      message: string
      openOptions?: boolean
      openBusinessUnitSheet?: boolean
      assignmentErrors?: AssignmentFormErrors
    }

export function validateChecklistCreateForm(values: {
  title: string
  businessUnitId: string
  taskValues: string[]
  assignmentMode: 'none' | 'create_now'
  assignmentValues?: AssignmentFormValues
}): ChecklistCreateValidationResult {
  if (!values.title.trim()) {
    return { ok: false, message: 'Le titre est obligatoire.' }
  }

  if (!values.businessUnitId.trim()) {
    return {
      ok: false,
      message: 'Sélectionnez un pôle d’activité.',
      openBusinessUnitSheet: true,
    }
  }

  const normalizedTasks = values.taskValues.map((task) => task.trim()).filter(Boolean)
  if (normalizedTasks.length === 0) {
    return { ok: false, message: 'Ajoutez au moins une tâche.' }
  }

  for (const taskValue of normalizedTasks) {
    const taskError = validateTask(taskValue)
    if (taskError) {
      return { ok: false, message: taskError }
    }
  }

  if (values.assignmentMode === 'create_now' && values.assignmentValues) {
    const assignmentErrors = validateAssignmentForm(values.assignmentValues)
    if (hasAssignmentFormErrors(assignmentErrors)) {
      return {
        ok: false,
        message: 'Complétez l’affectation dans Options.',
        openOptions: true,
        assignmentErrors,
      }
    }
  }

  return { ok: true }
}
