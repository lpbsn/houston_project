import type { PermissionHints, SignalFeedItem } from '../types'

export const SIGNAL_CANCEL_CONFIRM_MESSAGE =
  'Confirmer l’annulation de cette observation ? Cette action est définitive.'

export const SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE =
  'Confirmer le marquage comme intéressant ? Cette action n’est pas réversible pour l’instant.'

export const SIGNAL_ARCHIVE_CONFIRM_MESSAGE =
  'Confirmer l’archivage de cette observation ? Cette action est définitive.'

export type SignalFeedCardActionId =
  | 'pin'
  | 'mark_interesting'
  | 'archive'
  | 'resolve'
  | 'cancel'
  | 'qualify'

export type SignalFeedCardActionTone = 'neutral' | 'success' | 'danger'

export type SignalFeedCardActionOption = {
  id: SignalFeedCardActionId
  label: string
  tone: SignalFeedCardActionTone
}

export function canOpenSignalFeedCardActions(hints: PermissionHints): boolean {
  return (
    hints.can_pin ||
    hints.can_mark_interesting ||
    hints.can_archive ||
    hints.can_resolve ||
    hints.can_cancel ||
    hints.can_qualify_routing
  )
}

export function getSignalFeedCardActionOptions(
  item: Pick<SignalFeedItem, 'permission_hints' | 'is_pinned'>,
): SignalFeedCardActionOption[] {
  const options: SignalFeedCardActionOption[] = []
  const { permission_hints: hints, is_pinned: isPinned } = item

  if (hints.can_qualify_routing) {
    options.push({
      id: 'qualify',
      label: 'Qualifier le routage',
      tone: 'neutral',
    })
  }

  if (hints.can_pin) {
    options.push({
      id: 'pin',
      label: isPinned ? 'Désépingler' : 'Épingler',
      tone: 'neutral',
    })
  }

  if (hints.can_mark_interesting) {
    options.push({
      id: 'mark_interesting',
      label: 'Marquer comme intéressant',
      tone: 'neutral',
    })
  }

  if (hints.can_archive) {
    options.push({
      id: 'archive',
      label: 'Archiver',
      tone: 'danger',
    })
  }

  if (hints.can_resolve) {
    options.push({
      id: 'resolve',
      label: 'Marquer comme résolue',
      tone: 'success',
    })
  }

  if (hints.can_cancel) {
    options.push({
      id: 'cancel',
      label: 'Annuler cette observation',
      tone: 'danger',
    })
  }

  return options
}
