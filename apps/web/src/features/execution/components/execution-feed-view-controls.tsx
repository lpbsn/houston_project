import { Calendar, List } from 'lucide-react'

import { TerrainFilterChip } from '@/components/ui/terrain'
import type { ActionPlanExecutionFeedCategory } from '@/features/action-plans/api'
import type { ActionPlanExecutionFeedSectionCounts } from '@/features/action-plans/types'
import { cn } from '@/lib/utils'

import { EXECUTION_FEED_CATEGORY_LABELS } from '../lib/action-plan-execution-feed-sections'
import type { ExecutionFeedLayout } from '../lib/execution-feed-url-state'

const OPERATIONAL_CATEGORIES: ActionPlanExecutionFeedCategory[] = [
  'all',
  'pending_validation',
  'overdue',
  'in_progress',
]
const TERMINAL_CATEGORIES: ActionPlanExecutionFeedCategory[] = ['done', 'canceled']

export function ExecutionFeedLayoutToggle({
  value,
  onChange,
}: {
  value: ExecutionFeedLayout
  onChange: (value: ExecutionFeedLayout) => void
}) {
  const options = [
    { value: 'list' as const, label: 'Liste', icon: List },
    { value: 'calendar' as const, label: 'Calendrier', icon: Calendar },
  ]
  return (
    <div role="tablist" aria-label="Disposition du feed" className="inline-flex items-center gap-0.5">
      {options.map((option) => {
        const selected = value === option.value
        const Icon = option.icon
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-label={option.label}
            className={cn(
              'inline-flex h-7 w-7 items-center justify-center rounded-md focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
              selected ? 'bg-[#F4F1EA] text-[#1a1a1a]' : 'text-[#A3A099]',
            )}
            onClick={() => onChange(option.value)}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
          </button>
        )
      })}
    </div>
  )
}

function executionCategoryCount(
  category: ActionPlanExecutionFeedCategory,
  counts: ActionPlanExecutionFeedSectionCounts | null | undefined,
): number | undefined {
  if (!counts) {
    return undefined
  }
  if (category === 'all') {
    return (
      counts.pending_validation +
      counts.overdue +
      counts.in_progress +
      counts.done +
      counts.canceled
    )
  }
  return counts[category]
}

export function ExecutionFeedCategoryChips({
  value,
  onChange,
  counts = null,
}: {
  value: ActionPlanExecutionFeedCategory
  onChange: (value: ActionPlanExecutionFeedCategory) => void
  counts?: ActionPlanExecutionFeedSectionCounts | null
}) {
  const categories = [
    ...OPERATIONAL_CATEGORIES,
    ...TERMINAL_CATEGORIES.filter((category) => (counts?.[category] ?? 0) > 0),
  ]
  return (
    <div role="group" aria-label="Catégorie du feed" className="flex flex-nowrap items-center gap-2">
      {categories.map((category) => {
        const count = executionCategoryCount(category, counts)
        const label = EXECUTION_FEED_CATEGORY_LABELS[category]
        return (
          <TerrainFilterChip
            key={category}
            pressed={value === category}
            className="shrink-0"
            onClick={() => onChange(category)}
          >
            {count == null ? label : `${label} · ${count}`}
          </TerrainFilterChip>
        )
      })}
    </div>
  )
}
