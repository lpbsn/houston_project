import { TerrainFilterChip } from '@/components/ui/terrain'
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
      ? counts.open +
          counts.in_progress +
          counts.interesting +
          counts.pinned +
          counts.retained
      : undefined
  }
  return counts[status]
}

function statusChipLabel(label: string, count: number | undefined): string {
  return count == null ? label : `${label} · ${count}`
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
  layout?: 'wrap' | 'scroll' | 'inline'
  className?: string
}) {
  const normalizedFilters = normalizeSignalFeedFilters(filters)
  const selected = selectedSignalFeedStatus(normalizedFilters)
  const terminalOptions = (
    [
      { value: 'resolved' as const, label: 'Résolus' },
      { value: 'canceled' as const, label: 'Annulés' },
    ] as const
  ).filter((option) => (counts?.[option.value] ?? 0) > 0)
  const options: Array<{ value: SignalFeedStatusSelection; label: string }> = [
    { value: 'all', label: 'Tout' },
    ...SIGNAL_FEED_STATUS_OPTIONS,
    ...terminalOptions,
  ]

  return (
    <div
      role="group"
      aria-label="Statut des observations"
      className={cn(
        'flex items-center gap-2',
        layout === 'scroll'
          ? 'min-w-0 flex-nowrap overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
          : layout === 'inline'
            ? 'shrink-0 flex-nowrap'
            : 'flex-wrap',
        className,
      )}
    >
      {options.map((option) => {
        const pressed = selected === option.value
        const count = statusCount(option.value, selected, counts)
        return (
          <TerrainFilterChip
            key={option.value}
            pressed={pressed}
            onClick={() => onChange(signalFeedFiltersForStatus(normalizedFilters, option.value))}
          >
            {statusChipLabel(option.label, count)}
          </TerrainFilterChip>
        )
      })}
    </div>
  )
}
