import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'

import { formatSignalRelativeTime } from '../lib/signal-display'
import type { SignalDetail } from '../types'

type LinkedExecution = SignalDetail['linked_action_plan_executions'][number]

type SignalLinkedActionPlansSectionProps = {
  executions: LinkedExecution[]
  onSelect: (executionId: string) => void
}

type LinkedActionPlanCardProps = {
  execution: LinkedExecution
  onSelect: (executionId: string) => void
}

function LinkedActionPlanCard({ execution, onSelect }: LinkedActionPlanCardProps) {
  const activityAt = execution.last_activity_at || execution.created_at
  const activityLabel = `il y a ${formatSignalRelativeTime(activityAt)}`

  return (
    <TerrainCard className="p-3">
      <button type="button" className="w-full text-left" onClick={() => onSelect(execution.id)}>
        <div className="flex items-start justify-between gap-2">
          <p className="min-w-0 flex-1 text-sm font-semibold text-[#1a1a1a]">{execution.title}</p>
          <ActionPlanStatusBadge status={execution.status} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[#7D7B75]">
          <span>{execution.pilot_business_unit.label}</span>
          <span>{activityLabel}</span>
        </div>
      </button>
    </TerrainCard>
  )
}

export function SignalLinkedActionPlansSection({
  executions,
  onSelect,
}: SignalLinkedActionPlansSectionProps) {
  if (executions.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-2">
      <TerrainFieldLabel>Plans d&apos;action</TerrainFieldLabel>
      <div className="flex flex-col gap-2">
        {executions.map((execution) => (
          <LinkedActionPlanCard key={execution.id} execution={execution} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}
