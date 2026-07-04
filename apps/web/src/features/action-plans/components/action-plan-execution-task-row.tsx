import { AlertCircle, Check, MoreVertical } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatActionPlanTaskStatusLabel } from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'
import { terrainCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionPlanExecutionTaskRowProps = {
  task: ActionPlanTaskExecution
  canShowActions: boolean
  isMutationPending: boolean
  onMarkDone: () => void
  onCreateObservation: () => void
  onSkipRequest: () => void
}

function TaskCheckbox({
  checked,
  disabled,
  onClick,
  ariaLabel,
}: {
  checked: boolean
  disabled?: boolean
  onClick?: () => void
  ariaLabel: string
}) {
  if (checked) {
    return (
      <span className="flex h-11 w-11 shrink-0 items-center justify-center" aria-hidden>
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-[#1D9E75]">
          <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
        </span>
      </span>
    )
  }

  if (onClick) {
    return (
      <button
        type="button"
        className="flex h-11 w-11 shrink-0 items-center justify-center disabled:opacity-50"
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={onClick}
      >
        <span className="h-5 w-5 rounded-md border-2 border-[#D4D2CB] bg-white" />
      </button>
    )
  }

  return (
    <span className="flex h-11 w-11 shrink-0 items-center justify-center" aria-hidden>
      <span className="h-5 w-5 rounded-md border-2 border-[#D4D2CB] bg-white" />
    </span>
  )
}

export function ActionPlanExecutionTaskRow({
  task,
  canShowActions,
  isMutationPending,
  onMarkDone,
  onCreateObservation,
  onSkipRequest,
}: ActionPlanExecutionTaskRowProps) {
  const isDone = task.status === 'done'
  const isPending = task.status === 'pending'
  const isObservationCreated = task.status === 'observation_created'
  const isSkipped = task.status === 'skipped'
  const showPendingActions = isPending && canShowActions

  return (
    <div
      className={cn(
        terrainCardClassName('px-3 py-3'),
        isDone && 'opacity-70',
        isSkipped && 'opacity-60',
        isObservationCreated && 'border-[#f0d4cf] bg-[#fff5f3]',
      )}
    >
      <div className="flex items-start gap-1">
        {isObservationCreated ? (
          <span className="flex h-11 w-11 shrink-0 items-center justify-center" aria-hidden>
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-[#E24B4A]">
              <AlertCircle className="h-3.5 w-3.5 text-white" />
            </span>
          </span>
        ) : (
          <TaskCheckbox
            checked={isDone}
            disabled={!showPendingActions || isMutationPending}
            onClick={showPendingActions ? onMarkDone : undefined}
            ariaLabel={`Marquer « ${task.task} » comme terminée`}
          />
        )}

        <div className="min-w-0 flex-1 pt-2">
          <p className="text-sm font-medium text-[#1a1a1a]">{task.task}</p>
          {!isPending ? (
            <p className="mt-0.5 text-xs text-[#7D7B75]">
              {formatActionPlanTaskStatusLabel(task.status)}
            </p>
          ) : null}
        </div>

        {showPendingActions ? (
          <div className="flex shrink-0 items-center">
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-11 w-11 rounded-xl"
              aria-label="Actions sur la tâche"
              disabled={isMutationPending}
              onClick={onSkipRequest}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </div>
        ) : null}
      </div>

      {showPendingActions ? (
        <div className="mt-2 flex gap-2 pl-12">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-9 flex-1 rounded-xl text-xs"
            disabled={isMutationPending}
            onClick={onCreateObservation}
          >
            Observation
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-9 flex-1 rounded-xl text-xs"
            disabled={isMutationPending}
            onClick={onSkipRequest}
          >
            Passer
          </Button>
        </div>
      ) : null}
    </div>
  )
}
