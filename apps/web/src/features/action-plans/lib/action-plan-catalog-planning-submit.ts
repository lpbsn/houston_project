import { ActionPlansApiError } from '../api'
import type { ActionPlanPlanningSubmitRequest } from '../types'
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
import { isActionPlanScheduleConfigured } from './action-plan-schedule-form'

export type CatalogPlanningSubmit = {
  kind: 'planning'
  body: ActionPlanPlanningSubmitRequest
}

export type CatalogPlanningOptions = {
  canSchedule: boolean
  staffMode?: boolean
}

export type CatalogPlanningPrimaryKind = 'planning'

export const CATALOG_LAUNCH_EXECUTION_LABEL = "Lancer l'exécution"

function newItemId(): string {
  return crypto.randomUUID()
}

export function validateCatalogPlanningDraft(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
): Record<string, string> {
  if (draft.usePerAssigneeChronology) {
    return validatePerAssigneePlanningDraft(draft, {
      allowRepeat: options.canSchedule,
      requireCompatibleRepeats: false,
    })
  }

  return validateActionPlanEventPlanningDraft(draft, {
    requireAssignees: false,
    allowRepeat: options.canSchedule,
  })
}

function buildSharedPlanningItems(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean },
): ActionPlanPlanningSubmitRequest['items'] {
  if (hasGlobalRepeat(draft)) {
    const scheduleBodies = buildScheduleRequestsFromDraft(draft, options)
    const scheduleBody = scheduleBodies[0]
    if (!scheduleBody) {
      return []
    }
    return [
      {
        item_id: newItemId(),
        kind: 'schedule',
        assignees: scheduleBody.assignees,
        start_date: scheduleBody.start_date ?? null,
        end_date: scheduleBody.end_date,
        start_at: scheduleBody.start_at,
        end_at: scheduleBody.end_at,
        recurrence_days: scheduleBody.recurrence_days,
      },
    ]
  }

  const useBody = buildUseRequestFromDraft(draft, options)
  return [
    {
      item_id: newItemId(),
      kind: 'execution',
      assignees: useBody.assignees,
      start_at: useBody.start_at ?? null,
      end_at: useBody.end_at ?? null,
      visible_from: useBody.visible_from ?? null,
    },
  ]
}

function buildIndividualPlanningItems(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean },
): ActionPlanPlanningSubmitRequest['items'] {
  const items: ActionPlanPlanningSubmitRequest['items'] = []

  for (const assignee of draft.assignees) {
    if (!assignee.membershipId || !assignee.businessUnitId) {
      continue
    }
    if (assignee.repeatEnabled) {
      const startParts = splitIsoToDateAndTime(assignee.startAt)
      const endParts = splitIsoToDateAndTime(assignee.endAt)
      items.push({
        item_id: newItemId(),
        kind: 'schedule',
        primary_membership_id: assignee.membershipId,
        business_unit_id: assignee.businessUnitId,
        start_date: startParts.date.trim() || null,
        end_date: assignee.recurrenceEndDate.trim(),
        start_at: startParts.time,
        end_at: endParts.time,
        recurrence_days: [...assignee.recurrenceDays],
      })
      continue
    }

    items.push({
      item_id: newItemId(),
      kind: 'execution',
      primary_membership_id: assignee.membershipId,
      business_unit_id: assignee.businessUnitId,
      start_at: assignee.startAt.trim() || null,
      end_at: assignee.endAt.trim() || null,
      visible_from: assignee.visibleFrom.trim() || null,
    })
  }

  if (options.staffMode && items.length === 0) {
    const useBody = buildUseRequestFromDraft(draft, options)
    items.push({
      item_id: newItemId(),
      kind: 'execution',
      assignees: useBody.assignees,
      start_at: useBody.start_at ?? null,
      end_at: useBody.end_at ?? null,
      visible_from: useBody.visible_from ?? null,
    })
  }

  return items
}

export function resolveCatalogPlanningSubmit(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
): CatalogPlanningSubmit | undefined {
  const items = draft.usePerAssigneeChronology
    ? buildIndividualPlanningItems(draft, { staffMode: options.staffMode })
    : buildSharedPlanningItems(draft, { staffMode: options.staffMode })

  if (items.length === 0) {
    return undefined
  }

  return {
    kind: 'planning',
    body: {
      submission_id: crypto.randomUUID(),
      use_shared_chronology: !draft.usePerAssigneeChronology,
      items,
    },
  }
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

  if (
    draft.usePerAssigneeChronology &&
    hasPerAssigneeRepeat(draft) &&
    options.canSchedule &&
    buildOneShotAssigneesFromDraft(draft).length === 0
  ) {
    return buildScheduleRequestsFromDraft(draft, { staffMode: options.staffMode }).length === 0
  }

  return false
}

function formatExecutionNoun(count: number): string {
  return count === 1 ? '1 exécution' : `${count} exécutions`
}

function formatScheduleNoun(count: number): string {
  return count === 1 ? '1 planification' : `${count} planifications`
}

export function formatPlanningSubmitFeedback(summary: {
  executions_created: number
  schedules_created: number
}): string {
  const schedules = summary.schedules_created
  const executions = summary.executions_created

  if (schedules > 0 && executions > 0) {
    return `${formatScheduleNoun(schedules)} et ${formatExecutionNoun(executions)} créées.`
  }
  if (schedules > 0) {
    return schedules === 1
      ? '1 planification créée.'
      : `${schedules} planifications créées.`
  }
  if (executions > 0) {
    return executions === 1 ? '1 exécution créée.' : `${executions} exécutions créées.`
  }
  return '0 exécution créée.'
}

export function resolveCatalogPlanningSubmitFallbackMessage(
  _submit: CatalogPlanningSubmit,
  error?: unknown,
): string {
  if (error instanceof ActionPlansApiError) {
    return error.message || 'Le plan n’a pas pu être utilisé.'
  }
  return 'Le plan n’a pas pu être utilisé.'
}
