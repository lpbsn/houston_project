import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  canShowActionPlanTaskCreateObservation,
  canShowActionPlanTaskSkip,
} from '../lib/action-plan-permission-hints'
import type { ActionPlanTaskExecution } from '../types'

export type ActionPlanTaskActionId = 'skip' | 'observation'

type ActionPlanTaskActionOption = {
  id: ActionPlanTaskActionId
  label: string
}

export function getActionPlanTaskActionOptions(
  task: ActionPlanTaskExecution,
  options: { isTerminal: boolean },
): ActionPlanTaskActionOption[] {
  const result: ActionPlanTaskActionOption[] = []

  if (canShowActionPlanTaskCreateObservation(task.permission_hints, { isTerminal: options.isTerminal, task })) {
    result.push({ id: 'observation', label: 'Créer une observation' })
  }

  if (canShowActionPlanTaskSkip(task.permission_hints, { isTerminal: options.isTerminal, task })) {
    result.push({ id: 'skip', label: 'Passer' })
  }

  return result
}

type ActionPlanExecutionTaskActionsSheetProps = {
  task: ActionPlanTaskExecution | null
  isTerminal: boolean
  open: boolean
  isPending: boolean
  onClose: () => void
  onSelectAction: (actionId: ActionPlanTaskActionId) => void
}

export function ActionPlanExecutionTaskActionsSheet({
  task,
  isTerminal,
  open,
  isPending,
  onClose,
  onSelectAction,
}: ActionPlanExecutionTaskActionsSheetProps) {
  const options = task ? getActionPlanTaskActionOptions(task, { isTerminal }) : []

  function handleSelect(actionId: ActionPlanTaskActionId) {
    if (isPending) {
      return
    }
    onSelectAction(actionId)
    onClose()
  }

  return (
    <TerrainBottomSheet title="Actions" open={open} onClose={onClose}>
      <ul className="flex flex-col gap-2">
        {options.map((option) => (
          <li key={option.id}>
            <button
              type="button"
              className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isPending}
              onClick={() => handleSelect(option.id)}
            >
              <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </TerrainBottomSheet>
  )
}
