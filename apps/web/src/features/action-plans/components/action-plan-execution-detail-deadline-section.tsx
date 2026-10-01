import { TerrainCard } from '@/components/ui/terrain'
import { TemporalProgressBar } from '@/features/execution/components/temporal-progress-bar'
import {
  computeTemporalProgressPercent,
  formatActionPlanFeedCardDateTimeLabel,
} from '@/features/execution/lib/action-plan-execution-feed-card-display'
import { useFeedCardNow } from '@/features/execution/lib/use-feed-card-now'
import { actionPlanExecutionDetailNavyBgClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  computeActionPlanDeadlineState,
  formatActionPlanAllDayInstantLabel,
  formatActionPlanEndAtLabel,
} from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailLabel } from './action-plan-execution-detail-label'

type ActionPlanExecutionDetailDeadlineSectionProps = {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
  isTerminal: boolean
  variant?: 'summary' | 'planification'
}

export function ActionPlanExecutionDetailDeadlineSection({
  execution,
  isOverdue,
  isTerminal,
  variant = 'summary',
}: ActionPlanExecutionDetailDeadlineSectionProps) {
  if (variant === 'planification') {
    return (
      <PlanificationDeadline
        execution={execution}
        isOverdue={isOverdue}
        isTerminal={isTerminal}
      />
    )
  }

  return <MobileEcheanceCard execution={execution} isOverdue={isOverdue} />
}

function MobileEcheanceCard({
  execution,
  isOverdue,
}: {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
}) {
  const now = useFeedCardNow()
  const startLabel = formatActionPlanFeedCardDateTimeLabel(execution.start_at, execution.all_day)
  const endLabel = formatActionPlanFeedCardDateTimeLabel(execution.end_at, execution.all_day)
  const showProgress = execution.status === 'in_progress'
  const progress =
    !showProgress || execution.all_day || !execution.start_at || !execution.end_at
      ? null
      : computeTemporalProgressPercent(execution.start_at, execution.end_at, now)
  const showOverdue = showProgress && isOverdue

  if (!startLabel && !endLabel && progress == null && !showOverdue && !execution.all_day) {
    return null
  }

  const compact =
    execution.status === 'pending_validation' ||
    execution.status === 'done' ||
    execution.status === 'canceled'

  return (
    <TerrainCard padding={compact ? 'sm' : 'md'} className={compact ? 'space-y-1.5' : 'space-y-2'}>
      <ActionPlanExecutionDetailLabel>Échéance</ActionPlanExecutionDetailLabel>
      {startLabel || endLabel ? (
        <div className="flex items-baseline justify-between gap-2 text-xs text-[#3d3d3d]">
          <span className="min-w-0 truncate">
            {startLabel ? (
              <>
                <span className="text-[#7D7B75]">Début</span> {startLabel}
              </>
            ) : null}
          </span>
          <span className="min-w-0 shrink-0 text-right">
            {endLabel ? (
              <>
                <span className="text-[#7D7B75]">Fin</span> {endLabel}
              </>
            ) : null}
          </span>
        </div>
      ) : null}
      {execution.all_day ? <p className="text-xs text-[#7D7B75]">Journée entière</p> : null}
      {showOverdue ? (
        <p className="text-xs font-medium text-[#E24B4A]">Échéance dépassée</p>
      ) : null}
      {progress != null ? (
        <TemporalProgressBar percent={isOverdue ? 100 : progress} />
      ) : null}
    </TerrainCard>
  )
}

function PlanificationDeadline({
  execution,
  isOverdue,
  isTerminal,
}: {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
  isTerminal: boolean
}) {
  if (!execution.start_at && !execution.end_at) {
    return null
  }

  const startLabel = execution.all_day
    ? formatActionPlanAllDayInstantLabel(execution.start_at)
    : formatActionPlanEndAtLabel(execution.start_at)
  const deadlineState =
    execution.end_at && !execution.all_day
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
  const delayLabel = showOverdue ? (deadlineState?.remainingLabel ?? 'Échéance dépassée') : null

  return (
    <TerrainCard className="space-y-3">
      <ActionPlanExecutionDetailLabel>Planification</ActionPlanExecutionDetailLabel>
      {execution.start_at ? (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
            Début
          </p>
          <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{startLabel}</p>
        </div>
      ) : null}
      {execution.end_at ? (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
            Échéance
          </p>
          <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{endAtLabel}</p>
        </div>
      ) : null}
      {delayLabel ? (
        <p className="text-[12px] font-semibold leading-snug text-[#E24B4A]">{delayLabel}</p>
      ) : null}
      {deadlineState?.mode === 'progress' && deadlineState.progressPct != null ? (
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
      ) : null}
    </TerrainCard>
  )
}
