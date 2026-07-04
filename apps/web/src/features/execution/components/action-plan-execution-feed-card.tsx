import { Bell } from 'lucide-react'

import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import {
  terrainFeedCardBaseClassName,
  terrainFeedInteractiveCardClassName,
} from '@/lib/terrain-styles'
import { getDisplayNameInitials } from '@/features/actions/lib/action-display'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import {
  formatActionPlanEndAtLabel,
  formatActionPlanTaskStatusLabel,
} from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'

import {
  actionPlanFeedSignalClassificationInput,
  formatActionPlanFeedAssigneeDisplay,
  formatActionPlanFeedInvolvedPoleLabels,
  isActionPlanFeedPendingValidationCard,
} from '../lib/action-plan-execution-feed-card-display'

type ActionPlanExecutionFeedCardProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
}

function ActionPlanFeedTaskPreviews({ item }: { item: ActionPlanExecutionFeedItem }) {
  if (item.task_executions.length === 0) {
    return null
  }

  return (
    <ul className="mt-3 space-y-1 border-t border-[#F0EFE9] pt-3">
      {item.task_executions.map((task) => (
        <li key={`${item.id}-${task.position}`} className="flex items-start justify-between gap-2 text-[11px]">
          <span className="min-w-0 flex-1 truncate text-[#555]">{task.task}</span>
          <span className="shrink-0 text-[#888]">{formatActionPlanTaskStatusLabel(task.status)}</span>
        </li>
      ))}
    </ul>
  )
}

function ActionPlanFeedAssigneeRow({ item }: { item: ActionPlanExecutionFeedItem }) {
  const { visible, overflow } = formatActionPlanFeedAssigneeDisplay(item.assignees)
  if (visible.length === 0) {
    return null
  }

  const primaryInitials = getDisplayNameInitials(visible[0] ?? '')
  const assigneeLabel =
    overflow > 0 ? `${visible.join(', ')} +${overflow}` : visible.join(', ')

  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
      <div className="flex min-w-0 items-center gap-2">
        <div
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
          aria-hidden
        >
          {primaryInitials}
        </div>
        <span className="truncate text-[11px] text-[#888]">{assigneeLabel}</span>
      </div>
      <ActionPlanStatusBadge status={item.status} />
    </div>
  )
}

function PendingValidationActionPlanFeedCard({ item, onSelect }: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const endAtLabel = formatActionPlanEndAtLabel(item.end_at)

  return (
    <article
      className={terrainFeedCardBaseClassName(
        'border border-[#E69138] bg-[#FFF9ED] hover:border-[#E69138]/80',
      )}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center gap-1.5">
        <Bell className="h-4 w-4 shrink-0 text-[#E69138]" aria-hidden />
        <span className="truncate text-[13px] font-bold text-[#B45309]">En attente de validation</span>
      </div>

      <div className="my-2 border-t border-[#F0DFC8]" />

      {signalInput ? (
        <div className="mb-2 flex flex-wrap items-start gap-1.5">
          <SignalClassificationBadges signal={signalInput} />
        </div>
      ) : null}

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>
      {item.description_short ? (
        <p className="mt-1 line-clamp-2 text-[12px] text-[#666]">{item.description_short}</p>
      ) : null}

      <p className="mt-2 text-[11px] text-[#888]">Pôle pilote : {item.pilot_business_unit.label}</p>

      {endAtLabel ? (
        <p className={`mt-1 text-[11px] ${item.is_overdue ? 'text-[#E24B4A]' : 'text-[#888]'}`}>
          Échéance : {endAtLabel}
        </p>
      ) : null}

      <ActionPlanFeedTaskPreviews item={item} />
      <ActionPlanFeedAssigneeRow item={item} />
    </article>
  )
}

function ClassicActionPlanFeedCard({ item, onSelect }: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const involvedPoleLabels = formatActionPlanFeedInvolvedPoleLabels(item.involved_poles)
  const endAtLabel = formatActionPlanEndAtLabel(item.end_at)

  return (
    <article
      className={terrainFeedInteractiveCardClassName()}
      style={{ borderLeftColor: '#1B4FD8' }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      {signalInput ? (
        <div className="mb-2 flex flex-wrap items-start gap-1.5">
          <SignalClassificationBadges signal={signalInput} />
        </div>
      ) : null}

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>
      {item.description_short ? (
        <p className="mt-1 line-clamp-2 text-[12px] text-[#666]">{item.description_short}</p>
      ) : null}

      <div className="mt-2 space-y-1 text-[11px] text-[#888]">
        <p>Pôle pilote : {item.pilot_business_unit.label}</p>
        {involvedPoleLabels ? <p>Pôles impliqués : {involvedPoleLabels}</p> : null}
        {endAtLabel ? (
          <p className={item.is_overdue ? 'text-[#E24B4A]' : undefined}>Échéance : {endAtLabel}</p>
        ) : null}
      </div>

      <ActionPlanFeedTaskPreviews item={item} />
      <ActionPlanFeedAssigneeRow item={item} />
    </article>
  )
}

export function ActionPlanExecutionFeedCard({ item, onSelect }: ActionPlanExecutionFeedCardProps) {
  if (isActionPlanFeedPendingValidationCard(item)) {
    return <PendingValidationActionPlanFeedCard item={item} onSelect={onSelect} />
  }

  return <ClassicActionPlanFeedCard item={item} onSelect={onSelect} />
}
