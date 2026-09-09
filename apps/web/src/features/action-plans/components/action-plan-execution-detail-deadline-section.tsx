import { Timer } from 'lucide-react'
import type { ReactNode } from 'react'

import { TerrainCard } from '@/components/ui/terrain'
import { actionPlanExecutionDetailNavyBgClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  computeActionPlanDeadlineState,
  formatActionPlanAllDayInstantLabel,
  formatActionPlanEndAtLabel,
} from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'

type ActionPlanExecutionDetailDeadlineSectionProps = {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
  isTerminal: boolean
}

function DateSectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <TerrainCard className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
        {title}
      </p>
      {children}
    </TerrainCard>
  )
}

export function ActionPlanExecutionDetailDeadlineSection({
  execution,
  isOverdue,
  isTerminal,
}: ActionPlanExecutionDetailDeadlineSectionProps) {
  if (!execution.start_at && !execution.end_at) {
    return null
  }

  const startLabel = execution.all_day
    ? formatActionPlanAllDayInstantLabel(execution.start_at)
    : formatActionPlanEndAtLabel(execution.start_at)

  const deadlineState = execution.end_at && !execution.all_day
    ? computeActionPlanDeadlineState({
        startAt: execution.start_at,
        endAt: execution.end_at,
        isTerminal,
      })
    : null
  const endAtLabel = execution.all_day
    ? formatActionPlanAllDayInstantLabel(execution.end_at)
    : formatActionPlanEndAtLabel(execution.end_at)
  const showOverdue = isOverdue || Boolean(deadlineState?.isOverdue)

  return (
    <>
      {execution.start_at ? (
        <DateSectionCard title="Début">
          <p className="text-sm text-[#555]">{startLabel}</p>
        </DateSectionCard>
      ) : null}

      {execution.end_at ? (
        <DateSectionCard title="Deadline">
          {deadlineState?.mode === 'progress' && deadlineState.progressPct != null ? (
            <>
              <div className="h-1.5 overflow-hidden rounded-full bg-[#F0EFE9]">
                <div
                  className={cn(
                    'h-full rounded-full transition-[width]',
                    showOverdue ? 'bg-[#E24B4A]' : actionPlanExecutionDetailNavyBgClassName,
                  )}
                  style={{ width: `${deadlineState.progressPct}%` }}
                  role="progressbar"
                  aria-valuenow={deadlineState.progressPct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Progression vers l'échéance"
                />
              </div>
              <div className="flex items-center justify-between gap-3 text-xs">
                {deadlineState.remainingLabel ? (
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 font-semibold',
                      showOverdue ? 'text-[#E24B4A]' : 'text-[#222222]',
                    )}
                  >
                    <Timer className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    {deadlineState.remainingLabel}
                  </span>
                ) : (
                  <span />
                )}
                {deadlineState.beforeLabel ? (
                  <span className="text-[#7D7B75]">{deadlineState.beforeLabel}</span>
                ) : null}
              </div>
            </>
          ) : (
            <p className={cn('text-sm', showOverdue ? 'font-medium text-[#E24B4A]' : 'text-[#555]')}>
              {endAtLabel}
            </p>
          )}
        </DateSectionCard>
      ) : null}
    </>
  )
}
