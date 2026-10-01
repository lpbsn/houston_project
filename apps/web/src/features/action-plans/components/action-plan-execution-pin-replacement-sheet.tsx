import { PinOff } from 'lucide-react'

import { TerrainBottomSheet, TerrainDialog } from '@/components/ui/terrain'
import type { ActionPlanExecutionFeedPinReplacementCandidate } from '../types'

type ActionPlanExecutionPinReplacementSheetProps = {
  open: boolean
  candidates: ActionPlanExecutionFeedPinReplacementCandidate[]
  isPending: boolean
  presentation?: 'sheet' | 'dialog'
  onClose: () => void
  onReplace: (executionId: string) => void
}

export function ActionPlanExecutionPinReplacementSheet({
  open,
  candidates,
  isPending,
  presentation = 'sheet',
  onClose,
  onReplace,
}: ActionPlanExecutionPinReplacementSheetProps) {
  if (!open) {
    return null
  }

  const choices = (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-[#5c564e]">
        Trois plans sont déjà épinglés. Choisissez celui à remplacer.
      </p>
      <ul className="flex flex-col gap-2">
        {candidates.map((candidate) => (
          <li key={candidate.execution_id}>
            <button
              type="button"
              className="flex min-h-11 w-full items-center gap-3 rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isPending}
              onClick={() => onReplace(candidate.execution_id)}
            >
              <PinOff className="size-4 shrink-0 text-[#5c564e]" aria-hidden />
              <span className="min-w-0 flex-1 text-sm font-medium text-[#1a1a1a]">
                {candidate.title}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )

  if (presentation === 'dialog') {
    return (
      <TerrainDialog
        title="Remplacer une épingle"
        open
        dismissible={!isPending}
        onClose={onClose}
      >
        {choices}
      </TerrainDialog>
    )
  }

  return (
    <TerrainBottomSheet
      title="Remplacer une épingle"
      open
      dismissible={!isPending}
      onClose={onClose}
    >
      {choices}
    </TerrainBottomSheet>
  )
}
