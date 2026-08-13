import { forwardRef } from 'react'

import { TerrainStickyFooter } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { ActionPlanExecutionPermissionHints } from '../types'
import { ActionPlanExecutionLifecycleActions } from './action-plan-execution-lifecycle-actions'

type ActionPlanExecutionStickyFooterProps = {
  hints: ActionPlanExecutionPermissionHints
  isTerminal: boolean
  isPending: boolean
  mutationErrorMessage: string | null
  className?: string
  'data-testid'?: string
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

export const ActionPlanExecutionStickyFooter = forwardRef<
  HTMLElement,
  ActionPlanExecutionStickyFooterProps
>(function ActionPlanExecutionStickyFooter(
  {
    hints,
    isTerminal,
    isPending,
    mutationErrorMessage,
    className,
    'data-testid': dataTestId,
    onMarkDone,
    onValidate,
    onReopen,
    onCancel,
  },
  ref,
) {
  return (
    <TerrainStickyFooter
      ref={ref}
      className={cn('flex flex-col gap-2', className)}
      data-testid={dataTestId}
    >
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
})
