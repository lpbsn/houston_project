import type { PermissionHints, SignalFeedItem } from '../types'

export type SignalFeedCardActionId = 'pin' | 'urgency'

export type SignalFeedCardActionOption = {
  id: SignalFeedCardActionId
  label: string
}

export function canOpenSignalFeedCardActions(hints: PermissionHints): boolean {
  return hints.can_pin || hints.can_set_urgency
}

export function getSignalFeedCardActionOptions(
  item: Pick<SignalFeedItem, 'permission_hints' | 'is_pinned' | 'urgency'>,
): SignalFeedCardActionOption[] {
  const options: SignalFeedCardActionOption[] = []
  const { permission_hints: hints, is_pinned: isPinned, urgency } = item

  if (hints.can_pin) {
    options.push({
      id: 'pin',
      label: isPinned ? 'Désépingler' : 'Épingler',
    })
  }

  if (hints.can_set_urgency) {
    options.push({
      id: 'urgency',
      label: urgency === 'high' ? 'Priorité normale' : 'Marquer urgent',
    })
  }

  return options
}
