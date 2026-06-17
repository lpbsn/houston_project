import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import {
  DEADLINE_HOUR_OPTIONS,
  DEADLINE_MINUTE_OPTIONS,
} from '@/features/actions/lib/action-create-deadline'
import { ActionCreateSheetFooter } from '@/features/actions/components/action-create-sheet-footer'
import { cn } from '@/lib/utils'

type ChecklistTimeSheetProps = {
  title: string
  timeValue: string
  onClose: () => void
  onApply: (hours: string, minutes: string) => void
}

function pickerButtonClass(isSelected: boolean): string {
  if (isSelected) {
    return 'border-[#1B4FD8] bg-[#EEF4FF] text-[#1B4FD8]'
  }
  return 'border-[#E8E6DF] bg-white text-[#555]'
}

function splitTimeValue(value: string): { hours: string; minutes: string } {
  if (!value.trim()) {
    return { hours: '09', minutes: '00' }
  }
  const [hours = '09', minutes = '00'] = value.split(':')
  return { hours, minutes }
}

export function ChecklistTimeSheet({
  title,
  timeValue,
  onClose,
  onApply,
}: ChecklistTimeSheetProps) {
  const initial = splitTimeValue(timeValue)
  const [draftHours, setDraftHours] = useState(initial.hours)
  const [draftMinutes, setDraftMinutes] = useState(initial.minutes)

  function handleApply() {
    onApply(draftHours, draftMinutes)
    onClose()
  }

  return (
    <TerrainBottomSheet
      title={title}
      open
      onClose={onClose}
      footer={<ActionCreateSheetFooter onCancel={onClose} onApply={handleApply} />}
    >
      <div className="flex gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[#7D7B75]">
            Heures
          </span>
          <ul
            className="flex max-h-52 flex-col gap-1.5 overflow-y-auto overscroll-y-contain pr-1"
            role="listbox"
            aria-label={`${title} — heures`}
          >
            {DEADLINE_HOUR_OPTIONS.map((hour) => {
              const isSelected = draftHours === hour
              return (
                <li key={hour} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    className={cn(
                      'flex min-h-11 w-full items-center justify-center rounded-lg border text-sm font-medium tabular-nums transition',
                      pickerButtonClass(isSelected),
                    )}
                    onClick={() => setDraftHours(hour)}
                  >
                    {hour}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[#7D7B75]">
            Minutes
          </span>
          <ul
            className="flex max-h-52 flex-col gap-1.5 overflow-y-auto overscroll-y-contain pr-1"
            role="listbox"
            aria-label={`${title} — minutes`}
          >
            {DEADLINE_MINUTE_OPTIONS.map((minute) => {
              const isSelected = draftMinutes === minute
              return (
                <li key={minute} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    className={cn(
                      'flex min-h-11 w-full items-center justify-center rounded-lg border text-sm font-medium tabular-nums transition',
                      pickerButtonClass(isSelected),
                    )}
                    onClick={() => setDraftMinutes(minute)}
                  >
                    {minute}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </TerrainBottomSheet>
  )
}
