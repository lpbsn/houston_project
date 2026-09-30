import { Calendar, List } from 'lucide-react'

import { TerrainFilterChip } from '@/components/ui/terrain'
import type { ActionPlanExecutionFeedCategory } from '@/features/action-plans/api'
import { cn } from '@/lib/utils'

import { EXECUTION_FEED_CATEGORY_LABELS } from '../lib/action-plan-execution-feed-sections'
import type { ExecutionFeedLayout } from '../lib/execution-feed-url-state'

const CATEGORIES: ActionPlanExecutionFeedCategory[] = [
  'all',
  'pending_validation',
  'overdue',
  'in_progress',
]

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

export function ExecutionFeedCategoryChips({
  value,
  onChange,
}: {
  value: ActionPlanExecutionFeedCategory
  onChange: (value: ActionPlanExecutionFeedCategory) => void
}) {
  return (
    <div role="group" aria-label="Catégorie du feed" className="flex flex-nowrap items-center gap-2">
      {CATEGORIES.map((category) => (
        <TerrainFilterChip
          key={category}
          pressed={value === category}
          className="shrink-0"
          onClick={() => onChange(category)}
        >
          {EXECUTION_FEED_CATEGORY_LABELS[category]}
        </TerrainFilterChip>
      ))}
    </div>
  )
}
