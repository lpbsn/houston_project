import { useRef, useState } from 'react'

import type { ActionPlanExecutionFeedViewMode } from '../api'
import { ActionPlansApiError } from '../api'
import {
  usePinActionPlanExecutionMutation,
  useUnpinActionPlanExecutionMutation,
} from '../hooks'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import type { ActionPlanExecutionFeedCardActionId } from '../lib/action-plan-execution-feed-card-actions'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedPinReplacementCandidate,
} from '../types'

const PIN_LIMIT_ERROR_CODE = 'action_plan_execution_feed_pin_limit_reached'

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
  const [pinReplacement, setPinReplacement] = useState<{
    target: ActionPlanExecutionFeedItem
    candidates: ActionPlanExecutionFeedPinReplacementCandidate[]
  } | null>(null)
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

  function closePinReplacement() {
    if (pinMutation.isPending) {
      return
    }
    setPinReplacement(null)
  }

  function pinCallbacks(target: ActionPlanExecutionFeedItem) {
    return {
      onSuccess: () => {
        setActionError(null)
        setActionsOpen(false)
        setPinReplacement(null)
        syncActiveItem(null)
      },
      onError: (error: unknown) => {
        if (
          error instanceof ActionPlansApiError &&
          error.code === PIN_LIMIT_ERROR_CODE &&
          error.replacementCandidates.length > 0
        ) {
          setActionError(null)
          setActionsOpen(false)
          setPinReplacement({
            target,
            candidates: error.replacementCandidates,
          })
          return
        }
        setPinReplacement(null)
        setActionError(
          resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être épinglé.'),
        )
      },
    }
  }

  function replacePin(replaceExecutionId: string) {
    if (!pinReplacement) {
      return
    }
    pinMutation.mutate(
      {
        executionId: pinReplacement.target.id,
        replaceExecutionId,
      },
      pinCallbacks(pinReplacement.target),
    )
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

    if (target.is_pinned) {
      unpinMutation.mutate(target.id, pinCallbacks(target))
      return
    }
    pinMutation.mutate({ executionId: target.id }, pinCallbacks(target))
  }

  return {
    activeItem,
    actionsOpen,
    actionError,
    openActions,
    closeActions,
    clearActionError,
    pinReplacement,
    closePinReplacement,
    replacePin,
    runAction,
    isPending,
  }
}
