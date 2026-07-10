import { useRef, useState } from 'react'

import { resolveApiErrorMessage } from '@/lib/error-message'

import { SignalsApiError } from '../api'
import {
  useCancelSignalMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useSignalUrgencyMutation,
  useUnpinSignalMutation,
} from '../hooks'
import {
  SIGNAL_CANCEL_CONFIRM_MESSAGE,
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import type { SignalFeedFilters, SignalFeedItem, SignalViewMode } from '../types'

export type SignalFeedQuickActionResult = 'close' | 'stay-open' | 'abort'

type UseSignalFeedQuickActionsOptions = {
  establishmentId: string | null
  viewMode: SignalViewMode
  filters: SignalFeedFilters
}

export function useSignalFeedQuickActions({
  establishmentId,
  viewMode,
  filters,
}: UseSignalFeedQuickActionsOptions) {
  const cacheContext = { viewMode, filters }
  const [activeItem, setActiveItem] = useState<SignalFeedItem | null>(null)
  const [actionsOpen, setActionsOpen] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const activeItemRef = useRef<SignalFeedItem | null>(null)

  const pinMutation = usePinSignalMutation(establishmentId, cacheContext)
  const unpinMutation = useUnpinSignalMutation(establishmentId, cacheContext)
  const urgencyMutation = useSignalUrgencyMutation(establishmentId, cacheContext)
  const resolveMutation = useResolveSignalMutation(establishmentId)
  const cancelMutation = useCancelSignalMutation(establishmentId)

  const isPending =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    urgencyMutation.isPending ||
    resolveMutation.isPending ||
    cancelMutation.isPending

  function syncActiveItem(item: SignalFeedItem | null) {
    activeItemRef.current = item
    setActiveItem(item)
  }

  function openActions(item: SignalFeedItem) {
    setActionError(null)
    syncActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    setActionsOpen(false)
    setActionError(null)
    syncActiveItem(null)
  }

  function createLifecycleMutationCallbacks(signalId: string) {
    return {
      onSuccess: () => {
        if (activeItemRef.current?.id !== signalId) {
          return
        }
        setActionError(null)
        closeActions()
      },
      onError: (error: unknown) => {
        if (activeItemRef.current?.id !== signalId) {
          return
        }
        setActionError(
          resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'),
        )
      },
    }
  }

  function runAction(actionId: SignalFeedCardActionId): SignalFeedQuickActionResult {
    if (!activeItem) {
      return 'abort'
    }

    const signalId = activeItem.id

    switch (actionId) {
      case 'pin':
        if (activeItem.is_pinned) {
          void unpinMutation.mutate(signalId)
        } else {
          void pinMutation.mutate(signalId)
        }
        return 'close'
      case 'urgency':
        void urgencyMutation.mutate({
          signalId,
          urgency: activeItem.urgency === 'high' ? 'normal' : 'high',
        })
        return 'close'
      case 'resolve':
        setActionError(null)
        void resolveMutation.mutate(signalId, createLifecycleMutationCallbacks(signalId))
        return 'stay-open'
      case 'cancel':
        if (!window.confirm(SIGNAL_CANCEL_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        setActionError(null)
        void cancelMutation.mutate(signalId, createLifecycleMutationCallbacks(signalId))
        return 'stay-open'
      default: {
        const exhaustiveCheck: never = actionId
        return exhaustiveCheck
      }
    }
  }

  return {
    activeItem,
    actionsOpen,
    actionError,
    openActions,
    closeActions,
    runAction,
    isPending,
  }
}
