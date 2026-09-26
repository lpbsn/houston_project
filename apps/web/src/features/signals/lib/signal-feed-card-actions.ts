import type { PermissionHints, SignalFeedItem } from '../types'

export const SIGNAL_CANCEL_CONFIRM_MESSAGE =
  'Confirmer l’annulation de cette observation ? Cette action est définitive.'

export const SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE =
  'Confirmer le marquage comme intéressant ? Cette action n’est pas réversible pour l’instant.'

/** UX hint when resolve/cancel are unavailable because a linked action plan owns the lifecycle. */
export const SIGNAL_IN_PROGRESS_RESOLVE_VIA_ACTION_PLAN_HINT =
  'Cette observation sera résolue via son plan d’action.'

export type SignalFeedCardActionId =
  | 'pin'
  | 'mark_interesting'
  | 'qualify'
  | 'resolve'
  | 'cancel'

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
    hints.can_qualify_routing ||
    hints.can_resolve ||
    hints.can_cancel
  )
}

export function getSignalFeedCardActionOptions(
  item: Pick<SignalFeedItem, 'permission_hints' | 'is_pinned'>,
): SignalFeedCardActionOption[] {
  const options: SignalFeedCardActionOption[] = []
  const { permission_hints: hints, is_pinned: isPinned } = item

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

  if (hints.can_qualify_routing) {
    options.push({
      id: 'qualify',
      label: 'Qualifier',
      tone: 'neutral',
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

/** Lifecycle actions handled by useSignalFeedQuickActions — exclude qualify. */
export function isSignalFeedLifecycleActionId(
  actionId: SignalFeedCardActionId,
): actionId is Exclude<SignalFeedCardActionId, 'qualify'> {
  return actionId !== 'qualify'
}
