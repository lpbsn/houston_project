import { ClipboardCheck, Clock } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/features/actions/lib/action-display'
import {
  formatChecklistEndBeforeTimeLabel,
  formatChecklistExecutionStatusLabel,
  formatChecklistFeedBadgeLabel,
  formatChecklistProgressLabel,
} from '@/features/checklists/lib/checklist-display'
import type { ChecklistFeedItem } from '@/features/checklists/types'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { terrainFeedCardBaseClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ExecutionChecklistCardProps = {
  item: ChecklistFeedItem
  onSelect: (executionId: string) => void
}

function getTaskProgressPercent(treatedCount: number, totalCount: number): number {
  if (totalCount <= 0) {
    return 0
  }
  return Math.round((treatedCount / totalCount) * 100)
}

export function ExecutionChecklistCard({ item, onSelect }: ExecutionChecklistCardProps) {
  const endLabel = formatChecklistEndBeforeTimeLabel(item.end_at)
  const assigneeInitials = getDisplayNameInitials(item.assigned_to_display_name)
  const progressPercent = getTaskProgressPercent(
    item.progress_treated_count,
    item.progress_total_count,
  )
  const badgeLabel = formatChecklistFeedBadgeLabel()
  const borderColor = item.is_overdue ? '#E24B4A' : '#E69138'
  const progressBarColor = item.is_overdue ? '#E24B4A' : '#E69138'

  return (
    <article
      className={terrainFeedCardBaseClassName(
        cn(
          'border bg-white hover:border-opacity-80',
          item.is_overdue ? 'hover:border-[#E24B4A]/80' : 'hover:border-[#E69138]/80',
        ),
      )}
      style={{ borderColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-start gap-2">
          <ClipboardCheck
            className={cn(
              'mt-0.5 h-4 w-4 shrink-0',
              item.is_overdue ? 'text-[#E24B4A]' : 'text-[#E69138]',
            )}
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <h3 className="truncate text-[15px] font-bold text-[#1a1a1a]">{item.title}</h3>
              <HoustonBadge variant="amber" className="shrink-0 text-[8px]">
                {badgeLabel}
              </HoustonBadge>
              {item.is_overdue ? (
                <HoustonBadge variant="red" className="shrink-0 text-[8px]">
                  EN RETARD
                </HoustonBadge>
              ) : null}
            </div>
            {item.business_unit_label ? (
              <p className="mt-1 text-[12px] text-[#888]">{item.business_unit_label}</p>
            ) : null}
          </div>
        </div>
        {endLabel ? (
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
              item.is_overdue
                ? 'bg-[#FEF2F2] text-[#B91C1C]'
                : 'bg-[#FFF9ED] text-[#B45309]',
            )}
          >
            <Clock className="h-3 w-3" aria-hidden />
            {endLabel}
          </span>
        ) : null}
      </div>

      <div className="mt-3">
        <div
          className="h-1.5 overflow-hidden rounded-full bg-[#F0EFE9]"
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progression des tâches"
        >
          <div
            className="h-full rounded-full transition-[width]"
            style={{ width: `${progressPercent}%`, backgroundColor: progressBarColor }}
          />
        </div>
        <p className="mt-1.5 text-[11px] text-[#888]">
          {formatChecklistProgressLabel(item.progress_treated_count, item.progress_total_count)}{' '}
          tâches
        </p>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#FFF9ED] text-[10px] font-bold text-[#B45309]"
            aria-hidden
          >
            {assigneeInitials}
          </div>
          <span className="truncate text-[11px] text-[#888]">{item.assigned_to_display_name}</span>
        </div>
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[#7D7B75]">
          {formatChecklistExecutionStatusLabel(item.status)}
        </span>
      </div>
    </article>
  )
}
