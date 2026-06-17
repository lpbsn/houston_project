import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { ActionCreateSheetFooter } from '@/features/actions/components/action-create-sheet-footer'
import { cn } from '@/lib/utils'

type ChecklistDateSheetProps = {
  title: string
  value: string
  minDate?: string
  onClose: () => void
  onApply: (value: string) => void
}

export function ChecklistDateSheet({
  title,
  value,
  minDate,
  onClose,
  onApply,
}: ChecklistDateSheetProps) {
  const [draftDate, setDraftDate] = useState(value)

  function handleApply() {
    if (!draftDate) {
      return
    }
    onApply(draftDate)
    onClose()
  }

  return (
    <TerrainBottomSheet
      title={title}
      open
      onClose={onClose}
      footer={
        <ActionCreateSheetFooter
          applyDisabled={!draftDate}
          onCancel={onClose}
          onApply={handleApply}
        />
      }
    >
      <label className="flex flex-col gap-2">
        <span className="text-sm text-[#555]">Sélectionner une date</span>
        <input
          type="date"
          value={draftDate}
          min={minDate}
          onChange={(e) => setDraftDate(e.target.value)}
          className={cn(
            'min-h-12 w-full rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3',
            'text-base text-[#1a1a1a]',
          )}
          aria-label={title}
        />
      </label>
    </TerrainBottomSheet>
  )
}
