import type { ActionPlanCreateRequest, ActionPlanUseRequest, PatchedActionPlanUpdateRequest } from '../types'
import type {
  ActionPlanAssigneeDraft,
  ActionPlanCreateFormValues,
  ActionPlanTaskDraft,
} from './action-plan-form-validation'
import { buildActionPlanScheduleCreateRequest } from './action-plan-schedule-payload'

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

export function buildActionPlanTaskInputPayloads(
  tasks: ActionPlanTaskDraft[],
  pilotBusinessUnitId: string,
): NonNullable<ActionPlanCreateRequest['tasks']> {
  return buildTaskPayloads(tasks, pilotBusinessUnitId)
}

function buildTaskPayloads(
  tasks: ActionPlanTaskDraft[],
  pilotBusinessUnitId: string,
): ActionPlanCreateRequest['tasks'] {
  return tasks
    .filter((task) => task.task.trim())
    .map((task, index) => ({
      task: task.task.trim(),
      business_unit_id: task.businessUnitId || pilotBusinessUnitId,
      position: index + 1,
      description: task.description.trim(),
      deadline_at: task.deadlineAt ? (toIsoDateTime(task.deadlineAt) ?? null) : null,
      assigned_membership_id: task.assigneeMembershipId || null,
    }))
}

export function buildActionPlanUpdateRequest(
  values: Pick<
    ActionPlanCreateFormValues,
    'title' | 'description' | 'requiresValidation' | 'tasks' | 'pilotBusinessUnitId'
  >,
): PatchedActionPlanUpdateRequest {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    requires_validation: values.requiresValidation,
    tasks: buildTaskPayloads(values.tasks, values.pilotBusinessUnitId),
  }
}

export function buildActionPlanShellCreateRequest(
  values: Pick<
    ActionPlanCreateFormValues,
    'title' | 'description' | 'pilotBusinessUnitId' | 'requiresValidation' | 'tasks'
  >,
  options: { reusableForScheduling?: boolean } = {},
): ActionPlanCreateRequest {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    pilot_business_unit_id: values.pilotBusinessUnitId,
    requires_validation: values.requiresValidation,
    is_reusable: options.reusableForScheduling === true,
    tasks: buildTaskPayloads(values.tasks, values.pilotBusinessUnitId),
    assignees: [],
    use_shared_chronology: false,
    start_at: null,
    end_at: null,
    visible_from: null,
  }
}

export function buildActionPlanCreateRequest(
  values: ActionPlanCreateFormValues,
): ActionPlanCreateRequest {
  if (values.saveToLibrary) {
    return {
      title: values.title.trim(),
      description: values.description.trim(),
      pilot_business_unit_id: values.pilotBusinessUnitId,
      requires_validation: values.requiresValidation,
      is_reusable: true,
      tasks: buildTaskPayloads(values.tasks, values.pilotBusinessUnitId),
      assignees: [],
      use_shared_chronology: false,
      start_at: null,
      end_at: null,
      visible_from: null,
      ...(values.sourceSignalId ? { source_signal_id: values.sourceSignalId } : {}),
    }
  }

  const scheduleEnabled = values.schedule.enabled
  const assignees = buildAssigneePayloads(values.assignees, {
        useSharedChronology: values.useSharedChronology,
        sharedStartAt: values.sharedStartAt,
        sharedEndAt: values.sharedEndAt,
        sharedVisibleFrom: values.sharedVisibleFrom,
      })

  const schedule = buildActionPlanScheduleCreateRequest({
    schedule: values.schedule,
    assignees: values.assignees,
    useSharedChronology: values.useSharedChronology,
  })

  return {
    title: values.title.trim(),
    description: values.description.trim(),
    pilot_business_unit_id: values.pilotBusinessUnitId,
    requires_validation: values.requiresValidation,
    is_reusable: scheduleEnabled,
    tasks: buildTaskPayloads(values.tasks, values.pilotBusinessUnitId),
    assignees,
    use_shared_chronology: values.useSharedChronology,
    start_at: values.useSharedChronology ? toIsoDateTime(values.sharedStartAt) ?? null : null,
    end_at: values.useSharedChronology ? toIsoDateTime(values.sharedEndAt) ?? null : null,
    visible_from: values.useSharedChronology
      ? toIsoDateTime(values.sharedVisibleFrom) ?? null
      : null,
    ...(values.sourceSignalId ? { source_signal_id: values.sourceSignalId } : {}),
    ...(schedule ? { schedule } : {}),
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
