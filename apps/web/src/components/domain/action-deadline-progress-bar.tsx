import {
  formatActionDueByTimeLabel,
  formatActionRemainingTimeLabel,
  getActionDeadlineBarFillColor,
  getActionDeadlineRemainingPercent,
  isActionDeadlineCritical,
} from '@/features/actions/lib/action-display'
import { cn } from '@/lib/utils'

export type ActionDeadlineProgressBarProps = {
  createdAt: string
  dueAt: string
  isOverdue: boolean
  className?: string
}

export function ActionDeadlineProgressBar({
  createdAt,
  dueAt,
  isOverdue,
  className,
}: ActionDeadlineProgressBarProps) {
  const deadlineRemainingPercent = getActionDeadlineRemainingPercent(createdAt, dueAt)
  const fillColor = getActionDeadlineBarFillColor(deadlineRemainingPercent)
  const isDeadlineCritical = isActionDeadlineCritical({
    dueAt,
    isOverdue,
    createdAt,
  })

  return (
    <div className={className}>
      <div
        className="h-1 overflow-hidden rounded-full bg-[#F0EFE9]"
        role="progressbar"
        aria-valuenow={Math.round(deadlineRemainingPercent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progression vers l'échéance"
      >
        <div
          className="h-full rounded-full transition-[width]"
          style={{
            width: `${deadlineRemainingPercent}%`,
            backgroundColor: fillColor,
          }}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-2 text-[11px]">
        <span
          className={cn(isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#666]')}
        >
          {formatActionRemainingTimeLabel(dueAt, isOverdue)}
        </span>
        <span
          className={cn(
            'shrink-0',
            isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#888]',
          )}
        >
          {formatActionDueByTimeLabel(dueAt)}
        </span>
      </div>
    </div>
  )
}
