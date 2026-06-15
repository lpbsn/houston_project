import { Clock, MapPin } from 'lucide-react'

import {
  formatChecklistDeadlinePillLabel,
  formatChecklistProgressPercentLabel,
  formatChecklistProgressPointsLabel,
  getChecklistTaskProgressPercent,
} from '@/features/checklists/lib/checklist-display'
import { cn } from '@/lib/utils'

type ChecklistExecutionDetailHeaderProps = {
  title: string
  businessUnitLabel: string | null
  endAt: string | null
  isOverdue: boolean
  treatedCount: number
  totalCount: number
}

function ChecklistDeadlinePill({
  endAt,
  isOverdue,
}: {
  endAt: string
  isOverdue: boolean
}) {
  const label = formatChecklistDeadlinePillLabel(endAt)
  if (!label) {
    return null
  }

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
        isOverdue ? 'bg-[#FEF2F2] text-[#B91C1C]' : 'bg-[#FFF9ED] text-[#B45309]',
      )}
    >
      <Clock className="h-3 w-3" aria-hidden />
      {label}
    </span>
  )
}

export function ChecklistExecutionDetailHeader({
  title,
  businessUnitLabel,
  endAt,
  isOverdue,
  treatedCount,
  totalCount,
}: ChecklistExecutionDetailHeaderProps) {
  const progressPercent = getChecklistTaskProgressPercent(treatedCount, totalCount)
  const progressBarColor = isOverdue ? '#E24B4A' : '#E69138'

  return (
    <header className="space-y-2">
      {endAt ? (
        <div className="flex justify-end">
          <ChecklistDeadlinePill endAt={endAt} isOverdue={isOverdue} />
        </div>
      ) : null}

      <h1 className="text-xl font-bold text-[#1a1a1a]">{title}</h1>

      {businessUnitLabel ? (
        <p className="flex items-center gap-1 text-sm text-[#888]">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-[#E24B4A]" aria-hidden />
          {businessUnitLabel}
        </p>
      ) : null}

      <div>
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
        <div className="mt-1.5 flex items-center justify-between gap-2 text-[11px] text-[#888]">
          <span>{formatChecklistProgressPointsLabel(treatedCount, totalCount)}</span>
          <span className="shrink-0">{formatChecklistProgressPercentLabel(treatedCount, totalCount)}</span>
        </div>
      </div>
    </header>
  )
}
