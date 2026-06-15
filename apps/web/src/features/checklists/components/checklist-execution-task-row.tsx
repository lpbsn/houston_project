import { AlertCircle, Check, MoreVertical, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatChecklistTaskStatusLabel } from '@/features/checklists/lib/checklist-display'
import type { ChecklistTaskExecution } from '@/features/checklists/types'
import { terrainCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistExecutionTaskRowProps = {
  task: ChecklistTaskExecution
  canShowActions: boolean
  isMutationPending: boolean
  onMarkDone: () => void
  onReport: () => void
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
      <span
        className="flex h-11 w-11 shrink-0 items-center justify-center"
        aria-hidden
      >
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

export function ChecklistExecutionTaskRow({
  task,
  canShowActions,
  isMutationPending,
  onMarkDone,
  onReport,
  onSkipRequest,
}: ChecklistExecutionTaskRowProps) {
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

        <div className="min-w-0 flex-1 pt-2.5">
          <p
            className={cn(
              'text-sm font-medium leading-snug',
              isDone && 'text-[#7D7B75] line-through',
              isSkipped && 'text-[#7D7B75]',
              isObservationCreated && 'text-[#9a3b2e]',
              isPending && 'text-[#1a1a1a]',
            )}
          >
            {task.task}
          </p>

          {isObservationCreated ? (
            <p className="mt-1 text-xs text-[#9a3b2e]">
              {formatChecklistTaskStatusLabel('observation_created')}
            </p>
          ) : null}

          {isSkipped ? (
            <p className="mt-1 text-xs text-[#7D7B75]">
              {formatChecklistTaskStatusLabel('skipped')}
            </p>
          ) : null}
        </div>

        {showPendingActions ? (
          <div className="flex shrink-0 items-center">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-11 w-11 text-[#1B4FD8] hover:bg-[#1B4FD8]/5 hover:text-[#1B4FD8]"
              aria-label={`Signaler un problème pour « ${task.task} »`}
              disabled={isMutationPending}
              onClick={onReport}
            >
              <Plus className="h-5 w-5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-11 w-11 text-[#7D7B75] hover:bg-[#F0EFE9]"
              aria-label={`Passer la tâche « ${task.task} »`}
              disabled={isMutationPending}
              onClick={onSkipRequest}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
