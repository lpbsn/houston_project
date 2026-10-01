import { TerrainBottomSheet } from '@/components/ui/terrain'

import type { ActionPlanExecutionSecondaryAction } from '../lib/action-plan-permission-hints'

const secondaryActionLabels: Record<ActionPlanExecutionSecondaryAction, string> = {
  reopen: 'Rouvrir',
  cancel: 'Annuler',
}

type ActionPlanExecutionSecondaryActionsSheetProps = {
  actions: ActionPlanExecutionSecondaryAction[]
  open: boolean
  isPending: boolean
  onClose: () => void
  onReopen: () => void
  onCancel: () => void
}

export function ActionPlanExecutionSecondaryActionsSheet({
  actions,
  open,
  isPending,
  onClose,
  onReopen,
  onCancel,
}: ActionPlanExecutionSecondaryActionsSheetProps) {
  function handleSelect(action: ActionPlanExecutionSecondaryAction) {
    if (isPending) {
      return
    }
    onClose()
    if (action === 'reopen') {
      onReopen()
      return
    }
    onCancel()
  }

  return (
    <TerrainBottomSheet title="Actions" open={open} onClose={onClose}>
      <ul className="flex flex-col gap-2">
        {actions.map((action) => (
          <li key={action}>
            <button
              type="button"
              className="flex min-h-11 w-full items-center rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left text-sm font-medium text-[#1a1a1a] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isPending}
              onClick={() => handleSelect(action)}
            >
              {secondaryActionLabels[action]}
            </button>
          </li>
        ))}
      </ul>
    </TerrainBottomSheet>
  )
}
