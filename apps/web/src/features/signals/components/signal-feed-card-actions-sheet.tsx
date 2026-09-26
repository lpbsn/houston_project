import { createPortal } from 'react-dom'
import {
  Ban,
  CheckCircle2,
  Pin,
  Route,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  getSignalFeedCardActionOptions,
  type SignalFeedCardActionId,
  type SignalFeedCardActionTone,
} from '../lib/signal-feed-card-actions'
import { formatSignalRelativeTime } from '../lib/signal-display'
import type { SignalFeedQuickActionResult } from '../hooks/use-signal-feed-quick-actions'
import type { SignalFeedItem } from '../types'
import { SignalStatusBadge } from './signal-status-badge'

type SignalFeedCardActionsSheetProps = {
  item: SignalFeedItem
  open: boolean
  isPending: boolean
  errorMessage?: string | null
  onClose: () => void
  onSelectAction: (actionId: SignalFeedCardActionId) => SignalFeedQuickActionResult
}

const ACTION_ICONS: Record<SignalFeedCardActionId, LucideIcon> = {
  pin: Pin,
  mark_interesting: Sparkles,
  qualify: Route,
  resolve: CheckCircle2,
  cancel: Ban,
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
        <div className="mb-3 rounded-xl border border-[#E8E6DF] bg-[#F9F8F5] px-3 py-2.5">
          <div className="mb-1 flex items-center gap-1.5">
            <SignalStatusBadge status={item.status} variant="feed" />
            <span className="text-[11px] text-[#888]">
              {formatSignalRelativeTime(item.last_activity_at)}
            </span>
          </div>
          <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-[#1a1a1a]">
            {item.title}
          </p>
        </div>
        <ul className="flex flex-col gap-2">
          {options.map((option) => {
            const Icon = ACTION_ICONS[option.id]
            return (
              <li key={option.id}>
                <button
                  type="button"
                  className={cn(
                    'flex min-h-[52px] w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
                    actionButtonClassName(option.tone),
                  )}
                  disabled={isPending}
                  onClick={(event) => handleSelect(option.id, event)}
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
                  <span className={actionLabelClassName(option.tone)}>{option.label}</span>
                </button>
              </li>
            )
          })}
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
