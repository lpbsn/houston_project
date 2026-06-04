import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { ActionCreateSheetFooter } from './action-create-sheet-footer'

type ActionCreateDeadlineDateSheetProps = {
  limitDate: string
  onClose: () => void
  onApply: (date: string) => void
}

export function ActionCreateDeadlineDateSheet({
  limitDate,
  onClose,
  onApply,
}: ActionCreateDeadlineDateSheetProps) {
  const [draftDate, setDraftDate] = useState(limitDate)

  function handleApply() {
    if (!draftDate) {
      return
    }
    onApply(draftDate)
    onClose()
  }

  return (
    <TerrainBottomSheet
      title="Date limite"
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
          onChange={(e) => setDraftDate(e.target.value)}
          className={cn(
            'min-h-12 w-full rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3',
            'text-base text-[#1a1a1a]',
          )}
          aria-label="Date limite"
        />
      </label>
    </TerrainBottomSheet>
  )
}
