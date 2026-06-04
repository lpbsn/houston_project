import { ChevronRight } from 'lucide-react'
import { useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import type { DeadlinePreset } from '@/features/actions/lib/action-create-deadline'
import {
  formatDeadlineDateLabel,
  formatDeadlineTimeLabel,
} from '@/features/actions/lib/action-create-deadline'
import { cn } from '@/lib/utils'

import { ActionCreateDeadlineDateSheet } from './action-create-deadline-date-sheet'
import { ActionCreateDeadlineTimeSheet } from './action-create-deadline-time-sheet'

const PRESET_OPTIONS: { id: DeadlinePreset; label: string; accent?: 'danger' | 'warning' }[] = [
  { id: '30m', label: '30 min', accent: 'danger' },
  { id: '1h', label: '1 h', accent: 'warning' },
  { id: '2h', label: '2 h' },
  { id: '3h', label: '3 h' },
]

type OpenSheet = 'date' | 'time' | null

type ActionCreateDeadlineSectionProps = {
  selectedPreset: DeadlinePreset | null
  limitDate: string
  limitHours: string
  limitMinutes: string
  onPresetChange: (preset: DeadlinePreset) => void
  onLimitDateChange: (value: string) => void
  onLimitTimeChange: (hours: string, minutes: string) => void
}

function presetButtonClass(
  isSelected: boolean,
  accent?: 'danger' | 'warning',
): string {
  if (isSelected) {
    if (accent === 'danger') {
      return 'border-[#E24B4A] bg-[#FFF0F0] text-[#E24B4A]'
    }
    if (accent === 'warning') {
      return 'border-[#EF9F27] bg-[#FFF8EE] text-[#C76B00]'
    }
    return 'border-[#1B4FD8] bg-[#EEF4FF] text-[#1B4FD8]'
  }
  if (accent === 'danger') {
    return 'border-[#F5D0CF] bg-white text-[#E24B4A]'
  }
  if (accent === 'warning') {
    return 'border-[#F5E6D0] bg-white text-[#C76B00]'
  }
  return 'border-[#E8E6DF] bg-white text-[#555]'
}

function deadlineRowButtonClass(): string {
  return cn(
    'flex min-h-11 w-full items-center justify-between gap-3 rounded-lg border border-[#E8E6DF]',
    'bg-[#F5F4F0] px-3 py-2.5 text-left transition active:bg-[#EBEAE4]',
  )
}

export function ActionCreateDeadlineSection({
  selectedPreset,
  limitDate,
  limitHours,
  limitMinutes,
  onPresetChange,
  onLimitDateChange,
  onLimitTimeChange,
}: ActionCreateDeadlineSectionProps) {
  const [openSheet, setOpenSheet] = useState<OpenSheet>(null)

  const dateLabel = formatDeadlineDateLabel(limitDate)
  const timeLabel = formatDeadlineTimeLabel(limitHours, limitMinutes)

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Deadline</TerrainSectionLabel>
      <TerrainCard>
        <div className="flex flex-wrap gap-2">
          {PRESET_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              className={cn(
                'rounded-full border px-3.5 py-1.5 text-sm font-medium transition',
                presetButtonClass(selectedPreset === option.id, option.accent),
              )}
              onClick={() => onPresetChange(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-2 border-t border-[#F0EFE9] pt-4">
          <button
            type="button"
            className={deadlineRowButtonClass()}
            aria-label="Date limite"
            onClick={() => setOpenSheet('date')}
          >
            <span className="text-sm text-[#555]">Date limite</span>
            <span className="flex min-w-0 items-center gap-1">
              <span className="truncate text-sm font-medium text-[#1a1a1a]">{dateLabel}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
            </span>
          </button>

          <button
            type="button"
            className={deadlineRowButtonClass()}
            aria-label="Heure limite"
            onClick={() => setOpenSheet('time')}
          >
            <span className="text-sm text-[#555]">Heure limite</span>
            <span className="flex min-w-0 items-center gap-1">
              <span className="truncate text-sm font-medium tabular-nums text-[#1a1a1a]">
                {timeLabel}
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
            </span>
          </button>
        </div>
      </TerrainCard>

      {openSheet === 'date' ? (
        <ActionCreateDeadlineDateSheet
          key={limitDate}
          limitDate={limitDate}
          onClose={() => setOpenSheet(null)}
          onApply={onLimitDateChange}
        />
      ) : null}

      {openSheet === 'time' ? (
        <ActionCreateDeadlineTimeSheet
          key={`${limitHours}-${limitMinutes}`}
          limitHours={limitHours}
          limitMinutes={limitMinutes}
          onClose={() => setOpenSheet(null)}
          onApply={onLimitTimeChange}
        />
      ) : null}
    </section>
  )
}
