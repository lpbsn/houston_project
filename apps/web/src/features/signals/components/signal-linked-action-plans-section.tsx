import { TerrainCard } from '@/components/ui/terrain'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'

import type { SignalDetail } from '../types'

import { SignalDetailLabel } from './signal-detail-label'

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
  return (
    <TerrainCard>
      <button
        type="button"
        className="flex w-full items-center gap-2 text-left"
        onClick={() => onSelect(execution.id)}
      >
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-[#1a1a1a]">
          {execution.title}
        </p>
        <ActionPlanStatusBadge
          status={execution.status}
          validatedAt={execution.validated_at}
          variant="detail"
        />
        <span className="shrink-0 text-[13px] text-[#aaa]" aria-hidden>
          &gt;
        </span>
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
    <div className="flex flex-col gap-2.5">
      <SignalDetailLabel>Plans d&apos;action</SignalDetailLabel>
      <div className="flex flex-col gap-2.5">
        {executions.map((execution) => (
          <LinkedActionPlanCard key={execution.id} execution={execution} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}
