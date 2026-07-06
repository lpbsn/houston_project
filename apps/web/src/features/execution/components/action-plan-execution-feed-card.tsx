import { Bell } from 'lucide-react'

import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import {
  terrainFeedCardBaseClassName,
  terrainFeedInteractiveCardClassName,
} from '@/lib/terrain-styles'
import { getDisplayNameInitials } from '@/lib/display-names'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import { formatActionPlanEndAtLabel } from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'

import {
  actionPlanFeedSignalClassificationInput,
  formatActionPlanFeedAssigneeDisplay,
  formatActionPlanFeedTaskProgressLabel,
  isActionPlanFeedPendingValidationCard,
} from '../lib/action-plan-execution-feed-card-display'

type ActionPlanExecutionFeedCardProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
}

type ActionPlanFeedAssigneeRowProps = {
  item: ActionPlanExecutionFeedItem
  showStatusBadge?: boolean
}

function ActionPlanFeedMetaRow({ item }: { item: ActionPlanExecutionFeedItem }) {
  const progressLabel = formatActionPlanFeedTaskProgressLabel(item)
  const endAtLabel = formatActionPlanEndAtLabel(item.end_at)

  if (!progressLabel && !endAtLabel) {
    return null
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#888]">
      {progressLabel ? (
        <span className="font-medium tabular-nums text-[#555]">{progressLabel}</span>
      ) : null}
      {progressLabel && endAtLabel ? <span aria-hidden>·</span> : null}
      {endAtLabel ? (
        <span className={item.is_overdue ? 'font-medium text-[#E24B4A]' : undefined}>
          Échéance : {endAtLabel}
        </span>
      ) : null}
    </div>
  )
}

function ActionPlanFeedAssigneeRow({ item, showStatusBadge = true }: ActionPlanFeedAssigneeRowProps) {
  const { visible, overflow } = formatActionPlanFeedAssigneeDisplay(item.assignees)
  if (visible.length === 0 && !showStatusBadge) {
    return null
  }

  const primaryInitials = getDisplayNameInitials(visible[0] ?? '')
  const assigneeLabel =
    overflow > 0 ? `${visible.join(', ')} +${overflow}` : visible.join(', ')

  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
      {visible.length > 0 ? (
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
            aria-hidden
          >
            {primaryInitials}
          </div>
          <span className="truncate text-[11px] text-[#888]">{assigneeLabel}</span>
        </div>
      ) : (
        <span />
      )}
      {showStatusBadge ? <ActionPlanStatusBadge status={item.status} /> : null}
    </div>
  )
}

function PendingValidationActionPlanFeedCard({ item, onSelect }: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)

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

      <ActionPlanFeedMetaRow item={item} />

      <p className="mt-2 text-[11px] text-[#888]">Pôle pilote : {item.pilot_business_unit.label}</p>

      <ActionPlanFeedAssigneeRow item={item} showStatusBadge={false} />
    </article>
  )
}

function ClassicActionPlanFeedCard({ item, onSelect }: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)

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

      <ActionPlanFeedMetaRow item={item} />

      <p className="mt-2 text-[11px] text-[#888]">Pôle pilote : {item.pilot_business_unit.label}</p>

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
