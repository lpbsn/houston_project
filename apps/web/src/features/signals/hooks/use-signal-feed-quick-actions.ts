import { useRef, useState } from 'react'

import { resolveApiErrorMessage } from '@/lib/error-message'

import { SignalsApiError } from '../api'
import {
  useCancelSignalMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useUnpinSignalMutation,
} from '../hooks'
import {
  SIGNAL_CANCEL_CONFIRM_MESSAGE,
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import type { SignalFeedFilters, SignalFeedItem, SignalViewMode } from '../types'
import type { OpenSignalQualifySheetResult } from './use-signal-qualify-sheet'

export type SignalFeedQuickActionResult = 'close' | 'stay-open' | 'abort'

type UseSignalFeedQuickActionsOptions = {
  establishmentId: string | null
  viewMode: SignalViewMode
  filters: SignalFeedFilters
  onQualifyRequest?: (signalId: string) => Promise<OpenSignalQualifySheetResult>
}

export function useSignalFeedQuickActions({
  establishmentId,
  viewMode,
  filters,
  onQualifyRequest,
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

  const isLifecyclePending =
    resolveMutation.isPending || cancelMutation.isPending

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
    return actionId === 'resolve' || actionId === 'cancel'
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
      case 'qualify': {
        if (!onQualifyRequest) {
          return 'abort'
        }
        setActionError(null)
        void (async () => {
          const result = await onQualifyRequest(signalId)
          if (result.ok === false) {
            setActionError(result.message)
            return
          }
          resetActionsSheet()
        })()
        return 'stay-open'
      }
      case 'pin':
        if (activeItem.is_pinned) {
          void unpinMutation.mutate(signalId)
        } else {
          void pinMutation.mutate(signalId)
        }
        return 'close'
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
