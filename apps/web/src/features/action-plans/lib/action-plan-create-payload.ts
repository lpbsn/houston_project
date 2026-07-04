import type { ActionPlanCreateRequest, ActionPlanUseRequest } from '../types'
import type {
  ActionPlanAssigneeDraft,
  ActionPlanCreateFormValues,
  ActionPlanTaskDraft,
} from './action-plan-form-validation'

function toIsoDateTime(value: string): string | undefined {
  const trimmed = value.trim()
  if (!trimmed) {
    return undefined
  }
  const parsed = Date.parse(trimmed)
  if (Number.isNaN(parsed)) {
    return undefined
  }
  return new Date(parsed).toISOString()
}

function buildAssigneePayloads(
  assignees: ActionPlanAssigneeDraft[],
  options: {
    useSharedChronology: boolean
    sharedStartAt: string
    sharedEndAt: string
    sharedVisibleFrom: string
  },
): ActionPlanCreateRequest['assignees'] {
  return assignees
    .filter((assignee) => assignee.membershipId && assignee.businessUnitId)
    .map((assignee) => {
      const startAt = options.useSharedChronology
        ? toIsoDateTime(options.sharedStartAt)
        : toIsoDateTime(assignee.startAt)
      const endAt = options.useSharedChronology
        ? toIsoDateTime(options.sharedEndAt)
        : toIsoDateTime(assignee.endAt)
      const visibleFrom = options.useSharedChronology
        ? toIsoDateTime(options.sharedVisibleFrom)
        : toIsoDateTime(assignee.visibleFrom)

      return {
        membership_id: assignee.membershipId,
        business_unit_id: assignee.businessUnitId,
        start_at: startAt ?? null,
        end_at: endAt ?? null,
        visible_from: visibleFrom ?? null,
      }
    })
}

function buildTaskPayloads(tasks: ActionPlanTaskDraft[]): ActionPlanCreateRequest['tasks'] {
  return tasks
    .filter((task) => task.task.trim() && task.businessUnitId)
    .map((task, index) => ({
      task: task.task.trim(),
      business_unit_id: task.businessUnitId,
      position: index + 1,
    }))
}

export function buildActionPlanCreateRequest(
  values: ActionPlanCreateFormValues,
): ActionPlanCreateRequest {
  const assignees = values.saveToLibrary
    ? []
    : buildAssigneePayloads(values.assignees, {
        useSharedChronology: values.useSharedChronology,
        sharedStartAt: values.sharedStartAt,
        sharedEndAt: values.sharedEndAt,
        sharedVisibleFrom: values.sharedVisibleFrom,
      })

  return {
    title: values.title.trim(),
    description: values.description.trim(),
    pilot_business_unit_id: values.pilotBusinessUnitId,
    requires_validation: values.requiresValidation,
    is_reusable: values.saveToLibrary,
    tasks: buildTaskPayloads(values.tasks),
    assignees,
    use_shared_chronology: values.useSharedChronology,
    start_at: values.useSharedChronology ? toIsoDateTime(values.sharedStartAt) ?? null : null,
    end_at: values.useSharedChronology ? toIsoDateTime(values.sharedEndAt) ?? null : null,
    visible_from: values.useSharedChronology
      ? toIsoDateTime(values.sharedVisibleFrom) ?? null
      : null,
  }
}

export function buildActionPlanUseRequest(options: {
  assignees: ActionPlanAssigneeDraft[]
  useSharedChronology: boolean
  sharedStartAt: string
  sharedEndAt: string
  sharedVisibleFrom: string
}): ActionPlanUseRequest {
  return {
    assignees: buildAssigneePayloads(options.assignees, {
      useSharedChronology: options.useSharedChronology,
      sharedStartAt: options.sharedStartAt,
      sharedEndAt: options.sharedEndAt,
      sharedVisibleFrom: options.sharedVisibleFrom,
    }),
    use_shared_chronology: options.useSharedChronology,
    start_at: options.useSharedChronology ? toIsoDateTime(options.sharedStartAt) ?? null : null,
    end_at: options.useSharedChronology ? toIsoDateTime(options.sharedEndAt) ?? null : null,
    visible_from: options.useSharedChronology
      ? toIsoDateTime(options.sharedVisibleFrom) ?? null
      : null,
  }
}
