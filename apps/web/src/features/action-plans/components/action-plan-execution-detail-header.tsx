import { TerrainCard } from '@/components/ui/terrain'

import {
  countActionPlanTreatedTasks,
  formatActionPlanEndAtLabel,
} from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanStatusBadge } from './action-plan-status-badge'

type ActionPlanExecutionDetailHeaderProps = {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
}

export function ActionPlanExecutionDetailHeader({
  execution,
  isOverdue,
}: ActionPlanExecutionDetailHeaderProps) {
  const treatedCount = countActionPlanTreatedTasks(execution.task_executions)
  const totalCount = execution.task_executions.length
  const endAtLabel = formatActionPlanEndAtLabel(execution.end_at)

  return (
    <TerrainCard className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <h1 className="text-base font-semibold text-[#1a1a1a]">{execution.title}</h1>
        <ActionPlanStatusBadge status={execution.status} />
      </div>
      {execution.description ? (
        <p className="text-sm text-[#555]">{execution.description}</p>
      ) : null}
      <div className="flex flex-wrap gap-2 text-xs text-[#7D7B75]">
        <span>Pôle pilote : {execution.pilot_business_unit.label}</span>
        {totalCount > 0 ? (
          <span>
            Tâches : {treatedCount}/{totalCount}
          </span>
        ) : null}
        {endAtLabel ? (
          <span className={isOverdue ? 'text-[#E24B4A]' : undefined}>Échéance : {endAtLabel}</span>
        ) : null}
      </div>
      {execution.signal_summary ? (
        <p className="text-xs text-[#1B4FD8]">Signal lié : {execution.signal_summary.title}</p>
      ) : null}
    </TerrainCard>
  )
}
