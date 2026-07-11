import type { SignalClassificationInput } from '@/lib/signal-classification'

import { formatActionPlanEndAtLabel } from '@/features/action-plans/lib/action-plan-display'
import type {
  ActionPlanExecutionFeedAssignee,
  ActionPlanExecutionFeedItem,
} from '@/features/action-plans/types'

type InvolvedPoleLike = {
  business_unit?: {
    label?: string
  }
}

type SignalSummaryLike = {
  affected_business_unit_key?: string | null
  affected_business_unit_label?: string | null
  responsible_business_unit_key?: string | null
  responsible_business_unit_label?: string | null
  activity_subject_normalized_name?: string | null
  activity_subject_label?: string | null
}

const MAX_VISIBLE_ASSIGNEES = 3

export function isActionPlanFeedPendingValidationCard(item: ActionPlanExecutionFeedItem): boolean {
  return item.status === 'pending_validation'
}

export function actionPlanFeedSignalClassificationInput(
  signal: ActionPlanExecutionFeedItem['signal_summary'],
): SignalClassificationInput | null {
  if (!signal) {
    return null
  }
  const typed = signal as SignalSummaryLike
  return {
    affected_business_unit_key: typed.affected_business_unit_key,
    affected_business_unit_label: typed.affected_business_unit_label,
    responsible_business_unit_key: typed.responsible_business_unit_key,
    responsible_business_unit_label: typed.responsible_business_unit_label,
    activity_subject_normalized_name: typed.activity_subject_normalized_name,
    activity_subject_label: typed.activity_subject_label,
  }
}

export function formatActionPlanFeedInvolvedPoleLabels(
  involvedPoles: ActionPlanExecutionFeedItem['involved_poles'],
): string | null {
  if (involvedPoles.length <= 1) {
    return null
  }
  const labels = involvedPoles
    .map((pole) => (pole as InvolvedPoleLike).business_unit?.label?.trim())
    .filter((label): label is string => Boolean(label))
  if (labels.length <= 1) {
    return null
  }
  return labels.join(' · ')
}

export function formatActionPlanFeedAssigneeDisplay(
  assignees: ActionPlanExecutionFeedAssignee[],
): { visible: string[]; overflow: number } {
  const names = assignees
    .map((assignee) => assignee.display_name.trim())
    .filter((name) => name.length > 0)
  return {
    visible: names.slice(0, MAX_VISIBLE_ASSIGNEES),
    overflow: Math.max(0, names.length - MAX_VISIBLE_ASSIGNEES),
  }
}

export type ActionPlanFeedMetaParts = {
  deadlineLabel: string | null
  taskProgressLabel: string | null
}

export function formatActionPlanFeedTaskProgressLabel(
  item: Pick<ActionPlanExecutionFeedItem, 'task_count' | 'treated_task_count'>,
): string | null {
  if (item.task_count <= 0) {
    return null
  }
  return `Tâche ${item.treated_task_count}/${item.task_count}`
}

export function formatActionPlanFeedMetaParts(
  item: Pick<ActionPlanExecutionFeedItem, 'end_at' | 'task_count' | 'treated_task_count'>,
): ActionPlanFeedMetaParts {
  const endAtLabel = formatActionPlanEndAtLabel(item.end_at)
  return {
    deadlineLabel: endAtLabel ? `Échéance : ${endAtLabel}` : null,
    taskProgressLabel: formatActionPlanFeedTaskProgressLabel(item),
  }
}

export type ActionPlanFeedSidebarState =
  | { variant: 'countdown'; prefix: 'DANS'; value: string }
  | { variant: 'no_deadline' }
  | { variant: 'overdue' }

const MS_PER_HOUR = 60 * 60 * 1000
const MS_PER_DAY = 24 * MS_PER_HOUR

export function getActionPlanFeedSidebarState(
  endAt: string | null,
  now: number,
  isOverdue = false,
): ActionPlanFeedSidebarState {
  if (isOverdue) {
    return { variant: 'overdue' }
  }

  if (!endAt) {
    return { variant: 'no_deadline' }
  }

  const endMs = Date.parse(endAt)
  if (Number.isNaN(endMs)) {
    return { variant: 'no_deadline' }
  }

  const remainingMs = Math.max(0, endMs - now)
  if (remainingMs === 0) {
    return {
      variant: 'countdown',
      prefix: 'DANS',
      value: '0h',
    }
  }

  if (remainingMs >= MS_PER_DAY) {
    const days = Math.floor(remainingMs / MS_PER_DAY)
    return {
      variant: 'countdown',
      prefix: 'DANS',
      value: `${days}j`,
    }
  }

  const hours = Math.max(1, Math.ceil(remainingMs / MS_PER_HOUR))
  return {
    variant: 'countdown',
    prefix: 'DANS',
    value: `${hours}h`,
  }
}

export type ActionPlanFeedProgressState = {
  total: number
  filled: number
  fractionLabel: string
}

export function getActionPlanFeedProgressState(
  item: Pick<ActionPlanExecutionFeedItem, 'task_count' | 'treated_task_count'>,
): ActionPlanFeedProgressState | null {
  const total = Math.max(0, item.task_count)
  const filled = Math.min(total, Math.max(0, item.treated_task_count))

  if (total === 0) {
    return null
  }

  return {
    total,
    filled,
    fractionLabel: `${filled}/${total}`,
  }
}

export function isActionPlanFeedInProgressCard(item: ActionPlanExecutionFeedItem): boolean {
  return item.status === 'in_progress'
}

export function isActionPlanFeedDoneCard(item: ActionPlanExecutionFeedItem): boolean {
  return item.status === 'done'
}

export function isActionPlanFeedCanceledCard(item: ActionPlanExecutionFeedItem): boolean {
  return item.status === 'canceled'
}
