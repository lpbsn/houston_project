import { useRef, useState } from 'react'

import { resolveApiErrorMessage } from '@/lib/error-message'

import { SignalsApiError } from '../api'
import {
  useArchiveSignalMutation,
  useCancelSignalMutation,
  useMarkSignalInterestingMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useUnpinSignalMutation,
} from '../hooks'
import {
  SIGNAL_ARCHIVE_CONFIRM_MESSAGE,
  SIGNAL_CANCEL_CONFIRM_MESSAGE,
  SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE,
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
  const lifecycleLockRef = useRef(false)

  const pinMutation = usePinSignalMutation(establishmentId, cacheContext)
  const unpinMutation = useUnpinSignalMutation(establishmentId, cacheContext)
  const resolveMutation = useResolveSignalMutation(establishmentId)
  const cancelMutation = useCancelSignalMutation(establishmentId)
  const markInterestingMutation = useMarkSignalInterestingMutation(establishmentId)
  const archiveMutation = useArchiveSignalMutation(establishmentId)

  const isLifecyclePending =
    resolveMutation.isPending ||
    cancelMutation.isPending ||
    markInterestingMutation.isPending ||
    archiveMutation.isPending

  const isPending =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    isLifecyclePending

  function isLifecycleLocked() {
    return lifecycleLockRef.current || isLifecyclePending
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
    if (isLifecycleLocked()) {
      return
    }
    setActionError(null)
    syncActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    if (isLifecycleLocked()) {
      return
    }
    resetActionsSheet()
  }

  function createLifecycleMutationCallbacks() {
    return {
      onSuccess: () => {
        setActionError(null)
        resetActionsSheet()
      },
      onError: (error: unknown) => {
        setActionError(
          resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'),
        )
      },
      onSettled: () => {
        lifecycleLockRef.current = false
      },
    }
  }

  function startLifecycleMutation(
    mutate: (
      signalId: string,
      options: ReturnType<typeof createLifecycleMutationCallbacks>,
    ) => void,
    signalId: string,
  ): SignalFeedQuickActionResult {
    if (isLifecycleLocked()) {
      return 'abort'
    }
    setActionError(null)
    lifecycleLockRef.current = true
    mutate(signalId, createLifecycleMutationCallbacks())
    return 'stay-open'
  }

  function isLifecycleAction(actionId: SignalFeedCardActionId): boolean {
    return (
      actionId === 'resolve' ||
      actionId === 'cancel' ||
      actionId === 'mark_interesting' ||
      actionId === 'archive'
    )
  }

  function runAction(actionId: SignalFeedCardActionId): SignalFeedQuickActionResult {
    if (!activeItem) {
      return 'abort'
    }

    if (!isLifecycleAction(actionId) && isLifecycleLocked()) {
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
      case 'mark_interesting':
        if (!window.confirm(SIGNAL_MARK_INTERESTING_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        return startLifecycleMutation(
          (id, options) => void markInterestingMutation.mutate(id, options),
          signalId,
        )
      case 'archive':
        if (!window.confirm(SIGNAL_ARCHIVE_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        return startLifecycleMutation(
          (id, options) => void archiveMutation.mutate(id, options),
          signalId,
        )
      case 'resolve':
        return startLifecycleMutation(
          (id, options) => void resolveMutation.mutate(id, options),
          signalId,
        )
      case 'cancel':
        if (!window.confirm(SIGNAL_CANCEL_CONFIRM_MESSAGE)) {
          return 'abort'
        }
        return startLifecycleMutation(
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
