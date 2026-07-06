import type { ActionPlanScheduleCreateRequest } from '../types'
import type { ActionPlanAssigneeDraft } from './action-plan-form-validation'
import type { ActionPlanScheduleDraft } from './action-plan-schedule-form'
import { isActionPlanScheduleConfigured } from './action-plan-schedule-form'

function toScheduleTime(value: string): string | undefined {
  const trimmed = value.trim()
  if (!trimmed) {
    return undefined
  }
  if (/^\d{2}:\d{2}$/.test(trimmed)) {
    return `${trimmed}:00`
  }
  return trimmed
}

function toScheduleAssigneeTime(value: string): string | undefined {
  const trimmed = value.trim()
  if (!trimmed) {
    return undefined
  }
  if (/^\d{2}:\d{2}$/.test(trimmed)) {
    return `${trimmed}:00`
  }
  if (/^\d{2}:\d{2}:\d{2}$/.test(trimmed)) {
    return trimmed
  }
  const parsed = Date.parse(trimmed)
  if (Number.isNaN(parsed)) {
    return undefined
  }
  const date = new Date(parsed)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

function buildScheduleAssigneePayloads(
  assignees: ActionPlanAssigneeDraft[],
  useSharedChronology: boolean,
): ActionPlanScheduleCreateRequest['assignees'] {
  return assignees
    .filter((assignee) => assignee.membershipId && assignee.businessUnitId)
    .map((assignee) => {
      const payload = {
        membership_id: assignee.membershipId,
        business_unit_id: assignee.businessUnitId,
      }
      if (useSharedChronology) {
        return payload
      }
      return {
        ...payload,
        start_at: toScheduleAssigneeTime(assignee.startAt) ?? null,
        end_at: toScheduleAssigneeTime(assignee.endAt) ?? null,
      }
    })
}

export function buildActionPlanScheduleCreateRequest(options: {
  schedule: ActionPlanScheduleDraft
  assignees?: ActionPlanAssigneeDraft[]
  useSharedChronology?: boolean
}): ActionPlanScheduleCreateRequest | undefined {
  const { schedule, assignees = [], useSharedChronology = true } = options
  if (!isActionPlanScheduleConfigured(schedule)) {
    return undefined
  }

  const startAt = toScheduleTime(schedule.startAt)
  const endAt = toScheduleTime(schedule.endAt)
  if (!startAt || !endAt) {
    return undefined
  }

  return {
    start_date: schedule.startDate.trim() ? schedule.startDate.trim() : null,
    end_date: schedule.endDate.trim(),
    start_at: startAt,
    end_at: endAt,
    recurrence_days: [...schedule.recurrenceDays],
    assignees: buildScheduleAssigneePayloads(assignees, useSharedChronology),
    use_shared_chronology: useSharedChronology,
  }
}
