import { cn } from '@/lib/utils'

import {
  normalizeSignalFeedFilters,
  selectedSignalFeedStatus,
  SIGNAL_FEED_STATUS_OPTIONS,
  signalFeedFiltersForStatus,
  type SignalFeedFilters,
  type SignalFeedStatusSelection,
} from '../lib/signal-feed-filters'
import type { SignalFeedCounts } from '../types'

function statusCount(
  status: SignalFeedStatusSelection,
  selected: SignalFeedStatusSelection,
  counts: SignalFeedCounts | null | undefined,
): number | undefined {
  if (!counts) {
    return undefined
  }
  if (status === 'all') {
    // `pinned` is filtered by the active status. It represents every pin only
    // while Tout itself is selected.
    return selected === 'all'
      ? counts.open + counts.in_progress + counts.interesting + counts.pinned
      : undefined
  }
  return counts[status]
}

function statusChipLabel(label: string, count: number | undefined): string {
  return count == null ? label : `${label} · ${count}`
}

function filterChipClassName(active: boolean): string {
  return cn(
    'inline-flex h-8 shrink-0 items-center rounded-full border px-3 text-xs font-semibold whitespace-nowrap focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
    active
      ? 'border-[#1B4FD8] bg-[#EEF4FF] text-[#1B4FD8]'
      : 'border-[#E8E6DF] bg-white text-[#5c564e]',
  )
}

export function SignalFeedStatusChips({
  filters,
  counts = null,
  onChange,
  layout = 'wrap',
  className,
}: {
  filters: SignalFeedFilters
  counts?: SignalFeedCounts | null
  onChange: (filters: SignalFeedFilters) => void
  layout?: 'wrap' | 'scroll'
  className?: string
}) {
  const normalizedFilters = normalizeSignalFeedFilters(filters)
  const selected = selectedSignalFeedStatus(normalizedFilters)
  const options: Array<{ value: SignalFeedStatusSelection; label: string }> = [
    { value: 'all', label: 'Tout' },
    ...SIGNAL_FEED_STATUS_OPTIONS,
  ]

  return (
    <div
      role="group"
      aria-label="Statut des observations"
      className={cn(
        'flex items-center gap-2',
        layout === 'scroll'
          ? 'min-w-0 flex-nowrap overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
          : 'flex-wrap',
        className,
      )}
    >
      {options.map((option) => {
        const pressed = selected === option.value
        const count = statusCount(option.value, selected, counts)
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={pressed}
            className={filterChipClassName(pressed)}
            onClick={() => onChange(signalFeedFiltersForStatus(normalizedFilters, option.value))}
          >
            {statusChipLabel(option.label, count)}
          </button>
        )
      })}
    </div>
  )
}
