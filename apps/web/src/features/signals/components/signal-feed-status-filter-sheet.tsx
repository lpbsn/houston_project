import { useState } from 'react'

import {
  SIGNAL_FEED_STATUS_OPTIONS,
  type SignalFeedFilters,
  type SignalFeedStatusFilter,
} from '../lib/signal-feed-filters'
import { SignalFeedBottomSheet } from './signal-feed-bottom-sheet'
import { SignalFeedFilterPanelFooter } from './signal-feed-filter-panel-footer'

type SignalFeedStatusFilterSheetProps = {
  appliedFilters: SignalFeedFilters
  onClose: () => void
  onApply: (filters: SignalFeedFilters) => void
}

const ALL_STATUS_VALUES = SIGNAL_FEED_STATUS_OPTIONS.map((option) => option.value)

export function SignalFeedStatusFilterSheet({
  appliedFilters,
  onClose,
  onApply,
}: SignalFeedStatusFilterSheetProps) {
  const [draftStatuses, setDraftStatuses] = useState<SignalFeedStatusFilter[]>(() => [
    ...appliedFilters.statuses,
  ])

  function toggleStatus(value: SignalFeedStatusFilter) {
    setDraftStatuses((current) =>
      current.includes(value) ? current.filter((status) => status !== value) : [...current, value],
    )
  }

  function handleSelectAll() {
    setDraftStatuses([...ALL_STATUS_VALUES])
  }

  function handleClearAll() {
    setDraftStatuses([])
  }

  function handleApply() {
    onApply({
      ...appliedFilters,
      statuses: draftStatuses,
    })
    onClose()
  }

  return (
    <SignalFeedBottomSheet
      title="Statut"
      open
      onClose={onClose}
      footer={
        <SignalFeedFilterPanelFooter
          onSelectAll={handleSelectAll}
          onClearAll={handleClearAll}
          onCancel={onClose}
          onApply={handleApply}
        />
      }
    >
      <ul className="flex flex-col gap-2">
        {SIGNAL_FEED_STATUS_OPTIONS.map((option) => {
          const checked = draftStatuses.includes(option.value)
          return (
            <li key={option.value}>
              <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5">
                <input
                  type="checkbox"
                  className="size-4 rounded border-[#ccc] accent-[#1B4FD8]"
                  checked={checked}
                  onChange={() => toggleStatus(option.value)}
                />
                <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
              </label>
            </li>
          )
        })}
      </ul>
    </SignalFeedBottomSheet>
  )
}
