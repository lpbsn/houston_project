import { AlertCircle, Check, Minus } from 'lucide-react'

import { FeedCardActionsButton } from '@/components/domain/feed-card-meta-row'
import {
  formatActionPlanTaskDeadlineLabel,
  formatActionPlanTaskStatusLabel,
} from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'
import { actionPlanExecutionDetailTaskDoneClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionPlanExecutionTaskRowProps = {
  task: ActionPlanTaskExecution
  canShowMarkDone: boolean
  canShowUnmarkDone: boolean
  canShowSecondaryActions: boolean
  isMutationPending: boolean
  density?: 'default' | 'compact'
  onMarkDone: () => void
  onUnmarkDone: () => void
  onOpenActions: () => void
}

function TaskCheckbox({
  checked,
  disabled,
  onClick,
  ariaLabel,
  discrete = false,
}: {
  checked: boolean
  disabled?: boolean
  onClick?: () => void
  ariaLabel: string
  discrete?: boolean
}) {
  const hitClass = discrete ? 'h-11 w-11' : 'h-10 w-10'
  const markClass = discrete ? 'h-4 w-4' : 'h-5 w-5'
  const iconClass = discrete ? 'h-3 w-3' : 'h-3.5 w-3.5'

  if (checked && onClick) {
    return (
      <button
        type="button"
        className={cn('flex shrink-0 items-center justify-center disabled:opacity-50', hitClass)}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={onClick}
      >
        <span className={cn('flex items-center justify-center rounded-full bg-[#2D9C75]', markClass)}>
          <Check className={cn(iconClass, 'text-white')} strokeWidth={3} />
        </span>
      </button>
    )
  }

  if (checked) {
    return (
      <span className={cn('flex shrink-0 items-center justify-center', hitClass)} aria-hidden>
        <span className={cn('flex items-center justify-center rounded-full bg-[#2D9C75]', markClass)}>
          <Check className={cn(iconClass, 'text-white')} strokeWidth={3} />
        </span>
      </span>
    )
  }

  if (onClick) {
    return (
      <button
        type="button"
        className={cn('flex shrink-0 items-center justify-center disabled:opacity-50', hitClass)}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={onClick}
      >
        <span
          className={cn(
            'rounded-full border-[#D4D2CB] bg-white',
            discrete ? 'h-4 w-4 border' : 'h-5 w-5 border-2',
          )}
        />
      </button>
    )
  }

  return (
    <span className={cn('flex shrink-0 items-center justify-center', hitClass)} aria-hidden>
      <span
        className={cn(
          'rounded-full border-[#D4D2CB] bg-white',
          discrete ? 'h-4 w-4 border' : 'h-5 w-5 border-2',
        )}
      />
    </span>
  )
}

export function ActionPlanExecutionTaskRow({
  task,
  canShowMarkDone,
  canShowUnmarkDone,
  canShowSecondaryActions,
  isMutationPending,
  density = 'default',
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
  const poleLabel = task.business_unit?.specific_name ?? null
  const deadlineLabel = formatActionPlanTaskDeadlineLabel(task.deadline_at)
  const discrete = density !== 'compact'

  const statusHitClass = discrete ? 'h-11 w-11' : 'h-10 w-10'
  const statusIndicator = isObservationCreated ? (
    <span className={cn('flex shrink-0 items-center justify-center', statusHitClass)} aria-hidden>
      <span
        className={cn(
          'flex items-center justify-center rounded-full bg-[#E24B4A]',
          discrete ? 'h-4 w-4' : 'h-5 w-5',
        )}
      >
        <AlertCircle className={cn(discrete ? 'h-3 w-3' : 'h-3.5 w-3.5', 'text-white')} />
      </span>
    </span>
  ) : isSkipped ? (
    <span className={cn('flex shrink-0 items-center justify-center', statusHitClass)} aria-hidden>
      <span
        className={cn(
          'flex items-center justify-center rounded-full border border-[#D4D2CB] bg-[#E8E6DF]',
          discrete ? 'h-4 w-4' : 'h-5 w-5',
        )}
      >
        <Minus className="h-3 w-3 text-[#7D7B75]" strokeWidth={2.5} />
      </span>
    </span>
  ) : (
    <TaskCheckbox
      checked={isDone}
      discrete={discrete}
      disabled={(!showMarkDone && !showUnmarkDone) || isMutationPending}
      onClick={showMarkDone ? onMarkDone : showUnmarkDone ? onUnmarkDone : undefined}
      ariaLabel={
        showUnmarkDone
          ? `Marquer « ${task.task} » comme non terminée`
          : `Marquer « ${task.task} » comme terminée`
      }
    />
  )

  const actions = showSecondaryActions ? (
    <FeedCardActionsButton
      ariaLabel="Actions sur la tâche"
      disabled={isMutationPending}
      onClick={onOpenActions}
    />
  ) : null

  if (density === 'compact') {
    return (
      <div
        className={cn(
          'flex items-start gap-1 py-1.5',
          isObservationCreated && 'rounded-lg px-1',
        )}
      >
        {statusIndicator}
        <div className="min-w-0 flex-1 self-center">
          <p
            className={cn(
              'break-words text-[13px] font-normal leading-snug text-[#1a1a1a]',
              isDone && 'text-[#7D7B75] line-through decoration-[#B8B6B0]',
              isSkipped && 'text-[#7D7B75]',
            )}
          >
            {task.task}
          </p>
          {poleLabel ? (
            <p className="mt-0.5 break-words text-[11px] leading-snug text-[#9a958c]">{poleLabel}</p>
          ) : null}
          {task.description ? (
            <p className="mt-0.5 break-words whitespace-pre-wrap text-[12px] leading-snug text-[#7D7B75]">
              {task.description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="shrink-0 self-center">{actions}</div> : null}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex items-start gap-1 py-1',
        isSkipped && 'bg-[#F5F4F0]',
        isObservationCreated && 'bg-[#fff5f3]',
      )}
    >
      {statusIndicator}
      <div className="min-w-0 flex-1 self-center py-1.5">
        <p
          className={cn(
            'text-sm font-medium leading-snug text-[#1a1a1a]',
            isDone && 'text-[#7D7B75] line-through decoration-[#B8B6B0]',
            isSkipped && 'text-[#7D7B75]',
          )}
        >
          {task.task}
        </p>
        {poleLabel ? (
          <p className="mt-0.5 text-[12px] leading-snug text-[#9a958c]">{poleLabel}</p>
        ) : null}
        {deadlineLabel ? (
          <p className="mt-0.5 text-[12px] leading-snug text-[#7D7B75]">{`Échéance : ${deadlineLabel}`}</p>
        ) : null}
        {!isPending ? (
          <p
            className={cn(
              'mt-0.5 text-[12px] leading-snug',
              isDone && actionPlanExecutionDetailTaskDoneClassName,
              isSkipped && 'text-[#7D7B75]',
              isObservationCreated && 'text-[#E24B4A]',
            )}
          >
            {formatActionPlanTaskStatusLabel(task.status)}
          </p>
        ) : null}
        {task.description ? (
          <p className="mt-0.5 whitespace-pre-wrap text-[12px] leading-snug text-[#7D7B75]">
            {task.description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="shrink-0 self-center">{actions}</div> : null}
    </div>
  )
}
