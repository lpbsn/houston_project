import type { ReactNode } from 'react'
import { MoreHorizontal } from 'lucide-react'

import { cn } from '@/lib/utils'

type FeedCardMetaRowProps = {
  timeLabel: string
  badges?: ReactNode
  actions?: ReactNode
}

export function FeedCardMetaRow({ timeLabel, badges, actions }: FeedCardMetaRowProps) {
  return (
    <div className="mb-1 flex items-center justify-between gap-2">
      <div className="flex min-w-0 flex-wrap items-center gap-1">{badges}</div>
      <div className="flex shrink-0 items-center gap-0.5">
        <span className="text-[11px] leading-none text-[#888]">{timeLabel}</span>
        {actions}
      </div>
    </div>
  )
}

type FeedCardActionsButtonProps = {
  ariaLabel: string
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void
  disabled?: boolean
}

function stopCardNavigation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

export function FeedCardActionsButton({ ariaLabel, onClick, disabled }: FeedCardActionsButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[#7D7B75] hover:bg-black/5 disabled:pointer-events-none disabled:opacity-50',
      )}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={onClick}
      onKeyDown={stopCardNavigation}
    >
      <MoreHorizontal className="h-3.5 w-3.5" aria-hidden />
    </button>
  )
}
