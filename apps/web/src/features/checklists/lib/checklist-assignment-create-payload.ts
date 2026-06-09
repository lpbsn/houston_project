import type {
  ChecklistAssignment,
  ChecklistAssignmentCreateRequest,
  PatchedChecklistAssignmentUpdateRequest,
} from '@/features/checklists/types'

export type AssignmentFormValues = {
  assignedTo: string
  startDate: string
  endDate: string
  startAt: string
  endAt: string
  recurrenceDays: string[]
}

export function toApiTime(localValue: string): string {
  if (!localValue.trim()) {
    return ''
  }
  return localValue.length === 5 ? `${localValue}:00` : localValue
}

export function toFormTime(apiValue: string): string {
  if (!apiValue) {
    return ''
  }
  return apiValue.slice(0, 5)
}

export function assignmentToFormValues(assignment: ChecklistAssignment): AssignmentFormValues {
  return {
    assignedTo: assignment.assigned_to_id,
    startDate: assignment.start_date,
    endDate: assignment.end_date,
    startAt: toFormTime(assignment.start_at),
    endAt: toFormTime(assignment.end_at),
    recurrenceDays: assignment.recurrence_days ?? [],
  }
}

function buildAssignmentSchedulePayload(values: AssignmentFormValues) {
  const isOneShot = values.recurrenceDays.length === 0
  return {
    assigned_to: values.assignedTo,
    start_date: values.startDate,
    end_date: isOneShot ? values.startDate : values.endDate,
    start_at: toApiTime(values.startAt),
    end_at: toApiTime(values.endAt),
    recurrence_days: isOneShot ? null : values.recurrenceDays,
  }
}

export function buildChecklistAssignmentCreatePayload(
  values: AssignmentFormValues,
): ChecklistAssignmentCreateRequest {
  return buildAssignmentSchedulePayload(values)
}

export function buildChecklistAssignmentUpdatePayload(
  values: AssignmentFormValues,
): PatchedChecklistAssignmentUpdateRequest {
  return buildAssignmentSchedulePayload(values)
}
