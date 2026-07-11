import { AlertCircle, Check, Minus } from 'lucide-react'

import { FeedCardActionsButton } from '@/components/domain/feed-card-meta-row'
import {
  formatActionPlanTaskAssigneePoleLine,
  formatActionPlanTaskDeadlineLabel,
  formatActionPlanTaskStatusLabel,
} from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'
import { actionPlanExecutionDetailTaskDoneClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanTaskDetailLayout } from './action-plan-task-detail-layout'

type ActionPlanExecutionTaskRowProps = {
  task: ActionPlanTaskExecution
  canShowMarkDone: boolean
  canShowUnmarkDone: boolean
  canShowSecondaryActions: boolean
  isMutationPending: boolean
  onMarkDone: () => void
  onUnmarkDone: () => void
  onOpenActions: () => void
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
  if (checked && onClick) {
    return (
      <button
        type="button"
        className="flex h-10 w-10 shrink-0 items-center justify-center disabled:opacity-50"
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={onClick}
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#2D9C75]">
          <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
        </span>
      </button>
    )
  }

  if (checked) {
    return (
      <span className="flex h-10 w-10 shrink-0 items-center justify-center" aria-hidden>
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#2D9C75]">
          <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
        </span>
      </span>
    )
  }

  if (onClick) {
    return (
      <button
        type="button"
        className="flex h-10 w-10 shrink-0 items-center justify-center disabled:opacity-50"
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={onClick}
      >
        <span className="h-5 w-5 rounded-full border-2 border-[#D4D2CB] bg-white" />
      </button>
    )
  }

  return (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center" aria-hidden>
      <span className="h-5 w-5 rounded-full border-2 border-[#D4D2CB] bg-white" />
    </span>
  )
}

export function ActionPlanExecutionTaskRow({
  task,
  canShowMarkDone,
  canShowUnmarkDone,
  canShowSecondaryActions,
  isMutationPending,
  onMarkDone,
  onUnmarkDone,
  onOpenActions,
}: ActionPlanExecutionTaskRowProps) {
  const isDone = task.status === 'done'
  const isPending = task.status === 'pending'
  const isObservationCreated = task.status === 'observation_created'
  const isSkipped = task.status === 'skipped'
  const showMarkDone = isPending && canShowMarkDone
  const showUnmarkDone = isDone && canShowUnmarkDone
  const showSecondaryActions = isPending && canShowSecondaryActions
  const poleLabel = task.business_unit?.label ?? null
  const deadlineLabel = formatActionPlanTaskDeadlineLabel(task.deadline_at)
  const assigneePoleLine = formatActionPlanTaskAssigneePoleLine({
    assigneeDisplayName: task.assigned_display_name,
    poleLabel,
  })

  const statusIndicator = isObservationCreated ? (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center" aria-hidden>
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#E24B4A]">
        <AlertCircle className="h-3.5 w-3.5 text-white" />
      </span>
    </span>
  ) : isSkipped ? (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center" aria-hidden>
      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-[#D4D2CB] bg-[#E8E6DF]">
        <Minus className="h-3 w-3 text-[#7D7B75]" strokeWidth={2.5} />
      </span>
    </span>
  ) : (
    <TaskCheckbox
      checked={isDone}
      disabled={(!showMarkDone && !showUnmarkDone) || isMutationPending}
      onClick={showMarkDone ? onMarkDone : showUnmarkDone ? onUnmarkDone : undefined}
      ariaLabel={
        showUnmarkDone
          ? `Marquer « ${task.task} » comme non terminée`
          : `Marquer « ${task.task} » comme terminée`
      }
    />
  )

  return (
    <ActionPlanTaskDetailLayout
      className={cn(
        isSkipped && 'bg-[#F5F4F0]',
        isObservationCreated && 'rounded-lg border border-[#f0d4cf] bg-[#fff5f3]',
      )}
      leading={statusIndicator}
      title={
        <p
          className={cn(
            'text-base font-semibold text-[#222222]',
            isDone && 'text-[#7D7B75] line-through decoration-[#B8B6B0]',
            isSkipped && 'text-[#7D7B75]',
          )}
        >
          {task.task}
        </p>
      }
      meta={assigneePoleLine}
      actions={
        showSecondaryActions ? (
          <FeedCardActionsButton
            ariaLabel="Actions sur la tâche"
            disabled={isMutationPending}
            onClick={onOpenActions}
          />
        ) : null
      }
      deadline={deadlineLabel ? `Échéance : ${deadlineLabel}` : null}
      status={
        !isPending ? (
          <span
            className={cn(
              isDone && actionPlanExecutionDetailTaskDoneClassName,
              isSkipped && 'text-[#7D7B75]',
              isObservationCreated && 'text-[#E24B4A]',
            )}
          >
            {formatActionPlanTaskStatusLabel(task.status)}
          </span>
        ) : null
      }
      description={task.description || null}
    />
  )
}
