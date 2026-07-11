import type { ActionPlanAssigneeDraft } from './action-plan-form-validation'
import type { ActionPlanScheduleDraft } from './action-plan-schedule-form'
import { isActionPlanScheduleConfigured } from './action-plan-schedule-form'
import { buildActionPlanScheduleCreateRequest } from './action-plan-schedule-payload'
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest } from '../types'
import {
  buildOneShotAssigneesFromDraft,
  buildScheduleRequestsFromDraft,
  buildUseRequestFromDraft,
  hasGlobalRepeat,
  hasPerAssigneeRepeat,
  splitIsoToDateAndTime,
  toScheduleDraft,
  validateActionPlanEventPlanningDraft,
  validatePerAssigneePlanningDraft,
  type ActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'

export type CatalogPlanningSubmit =
  | { kind: 'use'; useBody: ActionPlanUseRequest }
  | { kind: 'schedule'; scheduleBody: ActionPlanScheduleCreateRequest }
  | {
      kind: 'mixed'
      scheduleBody: ActionPlanScheduleCreateRequest
      useBody: ActionPlanUseRequest
    }

export type CatalogPlanningOptions = {
  canSchedule: boolean
  staffMode?: boolean
}

export function validateCatalogPlanningDraft(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
): Record<string, string> {
  if (draft.usePerAssigneeChronology) {
    return validatePerAssigneePlanningDraft(draft, {
      allowRepeat: options.canSchedule,
      requireCompatibleRepeats: true,
    })
  }

  return validateActionPlanEventPlanningDraft(draft, {
    requireAssignees: false,
    allowRepeat: options.canSchedule,
  })
}

export function buildPerAssigneeScheduleFromAssignees(
  assignees: ActionPlanAssigneeDraft[],
  options: { staffMode?: boolean } = {},
): ActionPlanScheduleCreateRequest | undefined {
  const recurringAssignees = assignees.filter(
    (assignee) => assignee.repeatEnabled && assignee.membershipId && assignee.businessUnitId,
  )
  const firstAssignee = recurringAssignees[0]
  if (!firstAssignee) {
    return undefined
  }

  const startParts = splitIsoToDateAndTime(firstAssignee.startAt)
  const endParts = splitIsoToDateAndTime(firstAssignee.endAt)
  const schedule: ActionPlanScheduleDraft = {
    enabled: true,
    recurrenceDays: [...firstAssignee.recurrenceDays],
    startDate: startParts.date.trim(),
    endDate: firstAssignee.recurrenceEndDate.trim(),
    startAt: startParts.time,
    endAt: endParts.time,
  }

  return buildActionPlanScheduleCreateRequest({
    schedule,
    assignees: options.staffMode ? [] : recurringAssignees,
    useSharedChronology: false,
  })
}

export function buildPerAssigneeScheduleFromDraft(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean } = {},
): ActionPlanScheduleCreateRequest | undefined {
  return buildPerAssigneeScheduleFromAssignees(draft.assignees, options)
}

function hasOneShotAssignees(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean } = {},
): boolean {
  const assignees = options.staffMode
    ? draft.assignees.filter((assignee) => assignee.membershipId)
    : buildOneShotAssigneesFromDraft(draft)
  return assignees.length > 0
}

export function resolveCatalogPlanningSubmit(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
): CatalogPlanningSubmit | undefined {
  if (hasGlobalRepeat(draft) && options.canSchedule) {
    const scheduleBody = buildScheduleRequestsFromDraft(draft, {
      staffMode: options.staffMode,
    })[0]
    if (!scheduleBody) {
      return undefined
    }
    return { kind: 'schedule', scheduleBody }
  }

  if (draft.usePerAssigneeChronology) {
    const scheduleBody = buildPerAssigneeScheduleFromDraft(draft, {
      staffMode: options.staffMode,
    })
    const useBody = buildUseRequestFromDraft(draft, { staffMode: options.staffMode })
    const hasOneShot = hasOneShotAssignees(draft, { staffMode: options.staffMode })

    if (scheduleBody && hasOneShot) {
      return { kind: 'mixed', scheduleBody, useBody }
    }
    if (scheduleBody) {
      return { kind: 'schedule', scheduleBody }
    }
    if (hasOneShot) {
      return { kind: 'use', useBody }
    }
    return undefined
  }

  return {
    kind: 'use',
    useBody: buildUseRequestFromDraft(draft, { staffMode: options.staffMode }),
  }
}

export function resolveCatalogPlanningPrimaryLabel(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
): string {
  if (hasGlobalRepeat(draft) && options.canSchedule) {
    return 'Planifier la récurrence'
  }

  if (
    draft.usePerAssigneeChronology &&
    hasPerAssigneeRepeat(draft) &&
    !hasOneShotAssignees(draft, { staffMode: options.staffMode })
  ) {
    return 'Planifier la récurrence'
  }

  return "Lancer l'exécution"
}

export function isCatalogPlanningPrimaryDisabled(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions & { isPending: boolean },
): boolean {
  if (options.isPending) {
    return true
  }

  if (hasGlobalRepeat(draft) && options.canSchedule) {
    return !isActionPlanScheduleConfigured(toScheduleDraft(draft))
  }

  return false
}
