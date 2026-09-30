import { ChevronRight } from 'lucide-react'
import { useState } from 'react'

import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import { cn } from '@/lib/utils'

import type { SignalDetail } from '../types'

import { SignalDetailLabel } from './signal-detail-label'

const INITIAL_VISIBLE_LINKED_PLANS = 3

type LinkedExecution = SignalDetail['linked_action_plan_executions'][number]

type SignalLinkedActionPlansSectionProps = {
  executions: LinkedExecution[]
  onSelect: (executionId: string) => void
  alignWithCardText?: boolean
}

type LinkedActionPlanRowProps = {
  execution: LinkedExecution
  onSelect: (executionId: string) => void
  alignWithCardText: boolean
}

function LinkedActionPlanRow({ execution, onSelect, alignWithCardText }: LinkedActionPlanRowProps) {
  return (
    <button
      type="button"
      className={cn(
        'flex w-full items-center gap-2 rounded-lg border border-[#E8E6DF]/90 bg-[#FAFAF8] py-1.5 pr-2.5 text-left',
        alignWithCardText ? 'pl-4' : 'pl-2.5',
        'transition-colors hover:border-[#E8E6DF] hover:bg-white',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#114660]/25',
      )}
      onClick={() => onSelect(execution.id)}
    >
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-[12px] font-normal leading-snug text-[#1a1a1a]">
          {execution.title}
        </p>
        <div className="mt-0.5">
          <ActionPlanStatusBadge
            status={execution.status}
            validatedAt={execution.validated_at}
            variant="detail"
            className="px-1.5 py-0 text-[9px] leading-4"
          />
        </div>
      </div>
      <ChevronRight className="h-3 w-3 shrink-0 text-[#d4d2cb]" aria-hidden />
    </button>
  )
}

export function SignalLinkedActionPlansSection({
  executions,
  onSelect,
  alignWithCardText = false,
}: SignalLinkedActionPlansSectionProps) {
  const listKey = executions.map((execution) => execution.id).join('\0')
  const [expandedFor, setExpandedFor] = useState<string | null>(null)
  const expanded = expandedFor === listKey

  if (executions.length === 0) {
    return null
  }

  const visibleExecutions = expanded
    ? executions
    : executions.slice(0, INITIAL_VISIBLE_LINKED_PLANS)
  const hiddenCount = executions.length - visibleExecutions.length

  return (
    <div className="flex flex-col gap-1.5">
      <SignalDetailLabel className="text-[#7D7B75]">Plans d&apos;action</SignalDetailLabel>
      <div className="flex flex-col gap-1">
        {visibleExecutions.map((execution) => (
          <LinkedActionPlanRow
            key={execution.id}
            execution={execution}
            onSelect={onSelect}
            alignWithCardText={alignWithCardText}
          />
        ))}
      </div>
      {hiddenCount > 0 ? (
        <button
          type="button"
          className="self-start px-0.5 py-1 text-[12px] font-medium text-[#1B4FD8]"
          onClick={() => setExpandedFor(listKey)}
        >
          {hiddenCount === 1 ? "Voir l'autre plan" : `Voir les ${hiddenCount} autres plans`}
        </button>
      ) : null}
    </div>
  )
}
