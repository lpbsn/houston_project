import { TerrainStickyFooter } from '@/components/ui/terrain'

import type { ActionPlanExecutionPermissionHints } from '../types'
import { ActionPlanExecutionLifecycleActions } from './action-plan-execution-lifecycle-actions'

type ActionPlanExecutionStickyFooterProps = {
  hints: ActionPlanExecutionPermissionHints
  isTerminal: boolean
  isPending: boolean
  mutationErrorMessage: string | null
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

export function ActionPlanExecutionStickyFooter({
  hints,
  isTerminal,
  isPending,
  mutationErrorMessage,
  onMarkDone,
  onValidate,
  onReopen,
  onCancel,
}: ActionPlanExecutionStickyFooterProps) {
  return (
    <TerrainStickyFooter className="flex flex-col gap-2">
      <ActionPlanExecutionLifecycleActions
        hints={hints}
        isTerminal={isTerminal}
        isPending={isPending}
        onMarkDone={onMarkDone}
        onValidate={onValidate}
        onReopen={onReopen}
        onCancel={onCancel}
      />
      {mutationErrorMessage ? (
        <p className="px-1 text-sm text-destructive" role="alert">
          {mutationErrorMessage}
        </p>
      ) : null}
    </TerrainStickyFooter>
  )
}
