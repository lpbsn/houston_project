import { toApiTime } from '@/features/checklists/lib/checklist-assignment-create-payload'
import type { TemplateScheduleFormValues } from '@/features/checklists/lib/checklist-template-schedule-form'
import type { ChecklistTemplateScheduleRequest } from '@/features/checklists/types'

export function buildChecklistTemplateSchedulePayload(
  values: TemplateScheduleFormValues,
): ChecklistTemplateScheduleRequest {
  const payload: ChecklistTemplateScheduleRequest = {
    assigned_to: values.assignedTo,
    start_at: toApiTime(values.startAt),
    end_at: toApiTime(values.endAt),
  }

  if (values.recurrenceDays.length > 0) {
    payload.recurrence_days = values.recurrenceDays
    payload.recurrence_end_date = values.recurrenceEndDate
  }

  return payload
}
