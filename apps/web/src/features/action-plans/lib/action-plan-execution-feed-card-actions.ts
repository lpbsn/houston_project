import type { ActionPlanExecutionFeedItem } from '../types'

export type ActionPlanExecutionFeedCardActionId = 'pin'

export type ActionPlanExecutionFeedCardActionOption = {
  id: ActionPlanExecutionFeedCardActionId
  label: string
}

export function canOpenActionPlanExecutionFeedCardActions(
  hints: ActionPlanExecutionFeedItem['permission_hints'],
): boolean {
  return hints.can_pin
}

export function getActionPlanExecutionFeedCardActionOptions(
  item: Pick<ActionPlanExecutionFeedItem, 'permission_hints' | 'is_pinned'>,
): ActionPlanExecutionFeedCardActionOption[] {
  if (!item.permission_hints.can_pin) {
    return []
  }

  return [
    {
      id: 'pin',
      label: item.is_pinned ? 'Désépingler' : 'Épingler',
    },
  ]
}
