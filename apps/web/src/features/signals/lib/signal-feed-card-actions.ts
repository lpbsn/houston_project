import type { PermissionHints, SignalFeedItem } from '../types'

export const SIGNAL_CANCEL_CONFIRM_MESSAGE =
  'Confirmer l’annulation de ce signal ? Cette action est définitive.'

export type SignalFeedCardActionId = 'pin' | 'urgency' | 'resolve' | 'cancel'

export type SignalFeedCardActionTone = 'neutral' | 'success' | 'danger'

export type SignalFeedCardActionOption = {
  id: SignalFeedCardActionId
  label: string
  tone: SignalFeedCardActionTone
}

export function canOpenSignalFeedCardActions(hints: PermissionHints): boolean {
  return (
    hints.can_pin ||
    hints.can_set_urgency ||
    hints.can_resolve ||
    hints.can_cancel
  )
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
      tone: 'neutral',
    })
  }

  if (hints.can_set_urgency) {
    options.push({
      id: 'urgency',
      label: urgency === 'high' ? 'Priorité normale' : 'Marquer urgent',
      tone: 'neutral',
    })
  }

  if (hints.can_resolve) {
    options.push({
      id: 'resolve',
      label: 'Marquer résolu',
      tone: 'success',
    })
  }

  if (hints.can_cancel) {
    options.push({
      id: 'cancel',
      label: 'Annuler ce signal',
      tone: 'danger',
    })
  }

  return options
}
