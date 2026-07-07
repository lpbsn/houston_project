import { useState } from 'react'

import {
  usePinActionPlanExecutionMutation,
  useUnpinActionPlanExecutionMutation,
} from '../hooks'
import type { ActionPlanExecutionFeedCardActionId } from '../lib/action-plan-execution-feed-card-actions'
import type { ActionPlanExecutionFeedItem } from '../types'
import type { ActionPlanExecutionFeedViewMode } from '../api'

type UseActionPlanExecutionFeedQuickActionsOptions = {
  establishmentId: string | null
  viewMode: ActionPlanExecutionFeedViewMode
}

export function useActionPlanExecutionFeedQuickActions({
  establishmentId,
  viewMode,
}: UseActionPlanExecutionFeedQuickActionsOptions) {
  const [activeItem, setActiveItem] = useState<ActionPlanExecutionFeedItem | null>(null)
  const [actionsOpen, setActionsOpen] = useState(false)

  const pinMutation = usePinActionPlanExecutionMutation(establishmentId, viewMode)
  const unpinMutation = useUnpinActionPlanExecutionMutation(establishmentId, viewMode)

  const isPending = pinMutation.isPending || unpinMutation.isPending

  function openActions(item: ActionPlanExecutionFeedItem) {
    setActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    setActionsOpen(false)
    setActiveItem(null)
  }

  function runAction(actionId: ActionPlanExecutionFeedCardActionId) {
    if (!activeItem) {
      return
    }

    if (actionId === 'pin') {
      if (activeItem.is_pinned) {
        void unpinMutation.mutate(activeItem.id)
      } else {
        void pinMutation.mutate(activeItem.id)
      }
    }
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
