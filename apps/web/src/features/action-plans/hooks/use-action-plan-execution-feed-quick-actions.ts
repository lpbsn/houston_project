import { useRef, useState } from 'react'

import type { ActionPlanExecutionFeedViewMode } from '../api'
import {
  usePinActionPlanExecutionMutation,
  useUnpinActionPlanExecutionMutation,
} from '../hooks'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import type { ActionPlanExecutionFeedCardActionId } from '../lib/action-plan-execution-feed-card-actions'
import type { ActionPlanExecutionFeedItem } from '../types'

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
  const [actionError, setActionError] = useState<string | null>(null)
  const activeItemRef = useRef<ActionPlanExecutionFeedItem | null>(null)

  const pinMutation = usePinActionPlanExecutionMutation(establishmentId, viewMode)
  const unpinMutation = useUnpinActionPlanExecutionMutation(establishmentId, viewMode)

  const isPending = pinMutation.isPending || unpinMutation.isPending

  function syncActiveItem(item: ActionPlanExecutionFeedItem | null) {
    activeItemRef.current = item
    setActiveItem(item)
  }

  function openActions(item: ActionPlanExecutionFeedItem) {
    setActionError(null)
    syncActiveItem(item)
    setActionsOpen(true)
  }

  function closeActions() {
    setActionsOpen(false)
    syncActiveItem(null)
  }

  function clearActionError() {
    setActionError(null)
  }

  function runAction(
    actionId: ActionPlanExecutionFeedCardActionId,
    item?: ActionPlanExecutionFeedItem,
  ) {
    const target = item ?? activeItemRef.current
    if (!target) {
      return
    }
    if (item) {
      syncActiveItem(item)
    }

    if (actionId !== 'pin') {
      return
    }

    const callbacks = {
      onSuccess: () => {
        setActionError(null)
        setActionsOpen(false)
        syncActiveItem(null)
      },
      onError: (error: unknown) => {
        setActionError(
          resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être épinglé.'),
        )
      },
    }

    if (target.is_pinned) {
      unpinMutation.mutate(target.id, callbacks)
      return
    }
    pinMutation.mutate(target.id, callbacks)
  }

  return {
    activeItem,
    actionsOpen,
    actionError,
    openActions,
    closeActions,
    clearActionError,
    runAction,
    isPending,
  }
}
