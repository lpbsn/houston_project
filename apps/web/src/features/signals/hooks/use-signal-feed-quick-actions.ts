import { useRef, useState } from 'react'

import { resolveApiErrorMessage } from '@/lib/error-message'

import { SignalsApiError } from '../api'
import {
  useCancelSignalMutation,
  useMarkSignalInterestingMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useUnpinSignalMutation,
} from '../hooks'
import {
  SIGNAL_CANCEL_CONFIRM_MESSAGE,
  SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE,
  isSignalFeedLifecycleActionId,
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
  /** Blocks sheet dismiss / second actions until the in-flight mutation settles. */
  const actionLockRef = useRef(false)

  const pinMutation = usePinSignalMutation(establishmentId, cacheContext)
  const unpinMutation = useUnpinSignalMutation(establishmentId, cacheContext)
  const resolveMutation = useResolveSignalMutation(establishmentId, cacheContext)
  const cancelMutation = useCancelSignalMutation(establishmentId, cacheContext)
  const markInterestingMutation = useMarkSignalInterestingMutation(
    establishmentId,
    cacheContext,
  )

  const isPending =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    resolveMutation.isPending ||
    cancelMutation.isPending ||
    markInterestingMutation.isPending

  function isActionLocked() {
    return actionLockRef.current || isPending
  }

  function syncActiveItem(item: SignalFeedItem | null) {
    activeItemRef.current = item
    setActiveItem(item)
  }

  function resetActionsSheet() {
    setActionsOpen(false)
    setActionError(null)
    syncActiveItem(null)
  }

  function openActions(item: SignalFeedItem) {
    if (isActionLocked()) {
      return
    }
    setActionError(null)
    syncActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    if (isActionLocked()) {
      return
    }
    resetActionsSheet()
  }

  function createMutationCallbacks() {
    return {
      onSuccess: () => {
        setActionError(null)
        syncActiveItem(null)
      },
      onError: (error: unknown) => {
        setActionError(
          resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'),
        )
        // Reopen so the user can see the error after the optimistic close.
        setActionsOpen(true)
      },
      onSettled: () => {
        actionLockRef.current = false
      },
    }
  }

  function startLockedMutation(
    mutate: (signalId: string, options: ReturnType<typeof createMutationCallbacks>) => void,
    signalId: string,
  ): SignalFeedQuickActionResult {
    if (isActionLocked()) {
      return 'abort'
    }
    setActionError(null)
    actionLockRef.current = true
    mutate(signalId, createMutationCallbacks())
    // Close immediately; optimistic cache update makes the feed feel responsive.
    setActionsOpen(false)
    return 'close'
  }

  function runAction(
    actionId: SignalFeedCardActionId,
    item?: SignalFeedItem,
  ): SignalFeedQuickActionResult {
    const target = item ?? activeItemRef.current
    if (!target) {
      return 'abort'
    }
    if (item) {
      syncActiveItem(item)
    }

    if (!isSignalFeedLifecycleActionId(actionId)) {
      return 'abort'
    }

    if (isActionLocked()) {
      return 'abort'
    }

    const signalId = target.id

    switch (actionId) {
      case 'pin':
        return startLockedMutation((id, options) => {
          if (target.is_pinned) {
            void unpinMutation.mutate(id, options)
          } else {
            void pinMutation.mutate(id, options)
          }
        }, signalId)
      case 'mark_interesting':
        if (!window.confirm(SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        return startLockedMutation(
          (id, options) => void markInterestingMutation.mutate(id, options),
          signalId,
        )
      case 'resolve':
        return startLockedMutation(
          (id, options) => void resolveMutation.mutate(id, options),
          signalId,
        )
      case 'cancel':
        if (!window.confirm(SIGNAL_CANCEL_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        return startLockedMutation(
          (id, options) => void cancelMutation.mutate(id, options),
          signalId,
        )
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
