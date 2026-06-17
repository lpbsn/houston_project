import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { ActionCreateSheetFooter } from '@/features/actions/components/action-create-sheet-footer'
import {
  RECURRENCE_DAY_OPTIONS,
  toggleRecurrenceDay,
  type RecurrenceDay,
} from '@/features/checklists/lib/checklist-recurrence'
import { cn } from '@/lib/utils'

type ChecklistRecurrenceSheetProps = {
  recurrenceDays: string[]
  onClose: () => void
  onApply: (value: string[]) => void
}

export function ChecklistRecurrenceSheet({
  recurrenceDays,
  onClose,
  onApply,
}: ChecklistRecurrenceSheetProps) {
  const [draftDays, setDraftDays] = useState(recurrenceDays)

  function handleApply() {
    onApply(draftDays)
    onClose()
  }

  return (
    <TerrainBottomSheet
      title="Récurrence"
      open
      onClose={onClose}
      footer={<ActionCreateSheetFooter onCancel={onClose} onApply={handleApply} />}
    >
      <div className="space-y-2">
        <p className="text-xs text-[#7D7B75]">
          Laissez vide pour une exécution ponctuelle, ou sélectionnez les jours récurrents.
        </p>
        <div className="flex flex-wrap gap-2">
          {RECURRENCE_DAY_OPTIONS.map((option) => {
            const selected = draftDays.includes(option.value)
            return (
              <button
                key={option.value}
                type="button"
                onClick={() =>
                  setDraftDays(toggleRecurrenceDay(draftDays, option.value as RecurrenceDay))
                }
                className={cn(
                  'min-h-11 rounded-full px-3 text-xs font-medium transition-colors',
                  selected
                    ? 'bg-[#EEF2FF] text-[#1B4FD8]'
                    : 'bg-[#F0EFE9] text-[#7D7B75]',
                )}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      </div>
    </TerrainBottomSheet>
  )
}
