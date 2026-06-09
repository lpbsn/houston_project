export type AssignmentFormValues = {
  assignedTo: string
  startDate: string
  endDate: string
  startAt: string
  endAt: string
  recurrenceDays: string[]
}

export type AssignmentFormErrors = Partial<
  Record<
    'assignedTo' | 'startDate' | 'endDate' | 'startAt' | 'endAt' | 'recurrenceDays',
    string
  >
>

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

export function validateSharedTemplateCreate(values: {
  title: string
  businessUnitId: string
}): string | null {
  if (!values.title.trim()) {
    return 'Le titre est obligatoire.'
  }
  if (!values.businessUnitId.trim()) {
    return 'Le pôle est obligatoire pour une checklist partagée.'
  }
  return null
}

export function validatePersonalTemplateCreate(values: { title: string }): string | null {
  if (!values.title.trim()) {
    return 'Le titre est obligatoire.'
  }
  return null
}

export function validateTask(task: string): string | null {
  if (!task.trim()) {
    return 'La tâche est obligatoire.'
  }
  return null
}
