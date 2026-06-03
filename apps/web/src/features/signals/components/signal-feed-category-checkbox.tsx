import { useEffect, useRef } from 'react'

import type { FeedCategorySelectionState } from '../lib/signal-feed-category-selection'
import { cn } from '@/lib/utils'

type SignalFeedCategoryCheckboxProps = {
  compact?: boolean
  disabled?: boolean
  label: string
  levelLabel?: string
  onToggle: () => void
  selectionState: FeedCategorySelectionState
}

export function SignalFeedCategoryCheckbox({
  compact = false,
  disabled = false,
  label,
  levelLabel,
  onToggle,
  selectionState,
}: SignalFeedCategoryCheckboxProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = selectionState === 'indeterminate'
    }
  }, [selectionState])

  return (
    <label
      className={cn(
        'flex min-w-0 flex-1 cursor-pointer items-start gap-2',
        disabled && 'cursor-not-allowed opacity-60',
        compact && 'text-sm',
      )}
    >
      <input
        ref={inputRef}
        type="checkbox"
        checked={selectionState === 'checked'}
        disabled={disabled}
        onChange={onToggle}
        className="mt-0.5 size-4 shrink-0 rounded border-[#ccc] accent-[#1B4FD8]"
      />
      <span className="min-w-0 flex-1">
        {levelLabel ? (
          <span className="mb-0.5 block text-[9px] font-semibold uppercase tracking-[0.05em] text-[#7D7B75]">
            {levelLabel}
          </span>
        ) : null}
        <span className={cn('block font-medium text-[#1a1a1a]', compact && 'font-normal')}>
          {label}
        </span>
      </span>
    </label>
  )
}
