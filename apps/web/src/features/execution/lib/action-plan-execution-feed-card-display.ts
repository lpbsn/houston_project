import type { SignalClassificationInput } from '@/lib/signal-classification'

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
