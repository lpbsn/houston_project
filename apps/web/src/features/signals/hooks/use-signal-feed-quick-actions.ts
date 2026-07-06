import { useState } from 'react'

import {
  usePinSignalMutation,
  useSignalUrgencyMutation,
  useUnpinSignalMutation,
} from '../hooks'
import type { SignalFeedCardActionId } from '../lib/signal-feed-card-actions'
import type { SignalFeedFilters, SignalFeedItem, SignalViewMode } from '../types'

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

  const pinMutation = usePinSignalMutation(establishmentId, cacheContext)
  const unpinMutation = useUnpinSignalMutation(establishmentId, cacheContext)
  const urgencyMutation = useSignalUrgencyMutation(establishmentId, cacheContext)

  const isPending =
    pinMutation.isPending || unpinMutation.isPending || urgencyMutation.isPending

  function openActions(item: SignalFeedItem) {
    setActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    setActionsOpen(false)
    setActiveItem(null)
  }

  function runAction(actionId: SignalFeedCardActionId) {
    if (!activeItem) {
      return
    }

    if (actionId === 'pin') {
      if (activeItem.is_pinned) {
        void unpinMutation.mutate(activeItem.id)
      } else {
        void pinMutation.mutate(activeItem.id)
      }
      return
    }

    void urgencyMutation.mutate({
      signalId: activeItem.id,
      urgency: activeItem.urgency === 'high' ? 'normal' : 'high',
    })
  }

  return {
    activeItem,
    actionsOpen,
    openActions,
    closeActions,
    runAction,
    isPending,
  }
}
