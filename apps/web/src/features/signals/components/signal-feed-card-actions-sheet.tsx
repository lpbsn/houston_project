import { createPortal } from 'react-dom'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  getSignalFeedCardActionOptions,
  type SignalFeedCardActionId,
  type SignalFeedCardActionTone,
} from '../lib/signal-feed-card-actions'
import type { SignalFeedQuickActionResult } from '../hooks/use-signal-feed-quick-actions'
import type { SignalFeedItem } from '../types'

type SignalFeedCardActionsSheetProps = {
  item: SignalFeedItem
  open: boolean
  isPending: boolean
  errorMessage?: string | null
  onClose: () => void
  onSelectAction: (actionId: SignalFeedCardActionId) => SignalFeedQuickActionResult
}

function actionButtonClassName(tone: SignalFeedCardActionTone): string {
  switch (tone) {
    case 'success':
      return cn('rounded-lg border px-3 py-2.5', terrain.successSurface, terrain.success)
    case 'danger':
      return cn('rounded-lg border px-3 py-2.5', terrain.errorSurface, terrain.danger)
    case 'neutral':
      return 'rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5'
    default: {
      const exhaustiveCheck: never = tone
      return exhaustiveCheck
    }
  }
}

function actionLabelClassName(tone: SignalFeedCardActionTone): string {
  switch (tone) {
    case 'success':
      return cn('text-sm font-medium', terrain.success)
    case 'danger':
      return cn('text-sm font-medium', terrain.danger)
    case 'neutral':
      return 'text-sm font-medium text-[#1a1a1a]'
    default: {
      const exhaustiveCheck: never = tone
      return exhaustiveCheck
    }
  }
}

export function SignalFeedCardActionsSheet({
  item,
  open,
  isPending,
  errorMessage,
  onClose,
  onSelectAction,
}: SignalFeedCardActionsSheetProps) {
  const options = getSignalFeedCardActionOptions(item)

  function handleClose() {
    onClose()
  }

  function handleSelect(actionId: SignalFeedCardActionId, event: { stopPropagation: () => void }) {
    event.stopPropagation()
    if (isPending) {
      return
    }
    const result = onSelectAction(actionId)
    if (result === 'close') {
      handleClose()
    }
  }

  return createPortal(
    <div onClick={(event) => event.stopPropagation()}>
      <TerrainBottomSheet title="Actions" open={open} onClose={handleClose}>
        <ul className="flex flex-col gap-2">
          {options.map((option) => (
            <li key={option.id}>
              <button
                type="button"
                className={cn(
                  'flex min-h-11 w-full items-center justify-between text-left disabled:cursor-not-allowed disabled:opacity-50',
                  actionButtonClassName(option.tone),
                )}
                disabled={isPending}
                onClick={(event) => handleSelect(option.id, event)}
              >
                <span className={actionLabelClassName(option.tone)}>{option.label}</span>
              </button>
            </li>
          ))}
        </ul>
        {errorMessage ? (
          <p className="mt-2 px-1 text-sm text-destructive" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </TerrainBottomSheet>
    </div>,
    document.body,
  )
}
