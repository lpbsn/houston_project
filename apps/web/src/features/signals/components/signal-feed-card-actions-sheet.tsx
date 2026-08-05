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
      return cn(terrain.successSurface, terrain.success)
    case 'danger':
      return cn(terrain.errorSurface, terrain.danger)
    case 'neutral':
      return 'border-[#E8E6DF] bg-[#F5F4F0] text-[#1a1a1a]'
    default: {
      const exhaustiveCheck: never = tone
      return exhaustiveCheck
    }
  }
}

function actionLabelClassName(tone: SignalFeedCardActionTone): string {
  switch (tone) {
    case 'success':
      return cn('text-[15px] font-semibold', terrain.success)
    case 'danger':
      return cn('text-[15px] font-semibold', terrain.danger)
    case 'neutral':
      return 'text-[15px] font-semibold text-[#1a1a1a]'
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
        <ul className="flex flex-col gap-2.5">
          {options.map((option) => (
            <li key={option.id}>
              <button
                type="button"
                className={cn(
                  'flex min-h-[52px] w-full items-center justify-between rounded-lg border px-3 py-3 text-left transition active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
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
