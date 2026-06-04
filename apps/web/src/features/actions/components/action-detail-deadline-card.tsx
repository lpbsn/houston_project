import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { ActionDetail } from '../types'
import {
  formatActionDueByTimeLabel,
  formatActionRemainingTimeLabel,
  getActionDeadlineRemainingPercent,
  isActionDeadlineCritical,
} from '../lib/action-display'

type ActionDetailDeadlineCardProps = {
  action: Pick<ActionDetail, 'created_at' | 'due_at' | 'is_overdue'>
}

export function ActionDetailDeadlineCard({ action }: ActionDetailDeadlineCardProps) {
  const deadlineRemainingPercent = getActionDeadlineRemainingPercent(action.created_at, action.due_at)
  const isDeadlineCritical = isActionDeadlineCritical({
    dueAt: action.due_at,
    isOverdue: action.is_overdue,
    createdAt: action.created_at,
  })

  return (
    <TerrainCard>
      <TerrainFieldLabel>Deadline</TerrainFieldLabel>
      <div className="mt-3">
        <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
          <span
            className={cn(isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#666]')}
          >
            {formatActionRemainingTimeLabel(action.due_at, action.is_overdue)}
          </span>
          <span
            className={cn(
              'shrink-0',
              isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#888]',
            )}
          >
            {formatActionDueByTimeLabel(action.due_at)}
          </span>
        </div>
        <div
          className="h-1 overflow-hidden rounded-full bg-[#F0EFE9]"
          role="progressbar"
          aria-valuenow={Math.round(deadlineRemainingPercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progression vers l'échéance"
        >
          <div
            className={cn(
              'h-full rounded-full transition-[width]',
              isDeadlineCritical ? 'bg-[#E24B4A]' : 'bg-[#1B4FD8]',
            )}
            style={{ width: `${deadlineRemainingPercent}%` }}
          />
        </div>
      </div>
    </TerrainCard>
  )
}
