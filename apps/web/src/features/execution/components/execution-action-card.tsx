import { Bell } from 'lucide-react'

import type { ActionFeedItem } from '@/features/actions/types'
import { ActionStatusBadge } from '@/features/actions/components/action-status-badge'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { ActionDeadlineProgressBar } from '@/components/domain/action-deadline-progress-bar'
import {
  actionClassificationInput,
  formatActionCompletedByLabel,
  formatActionCreatorFooterLabel,
  formatActionValidationRelativeTime,
  formatActionValidationWaitingLabel,
  getActionCardLeftAccentColor,
  getActionLocationText,
  getDisplayNameInitials,
  isActionPendingValidationCard,
  resolveActionValidationRelativeTimeIso,
  shouldShowActionUrgentBadge,
} from '@/features/actions/lib/action-display'
import { HoustonBadge } from '@/components/ui/terrain'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import {
  terrainFeedCardBaseClassName,
  terrainFeedInteractiveCardClassName,
} from '@/lib/terrain-styles'
type ExecutionActionCardProps = {
  item: ActionFeedItem
  onSelect: (actionId: string) => void
}

function PendingValidationExecutionActionCard({
  item,
  onSelect,
}: ExecutionActionCardProps) {
  const showUrgentBadge = shouldShowActionUrgentBadge(item.signal_summary)
  const locationText = getActionLocationText(item.signal_summary)
  const assigneeInitials = getDisplayNameInitials(item.assigned_to_display_name)
  const completedByLabel = formatActionCompletedByLabel(item.assigned_to_display_name)
  const relativeTimeLabel = formatActionValidationRelativeTime(
    resolveActionValidationRelativeTimeIso(item),
  )

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
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Bell className="h-4 w-4 shrink-0 text-[#E69138]" aria-hidden />
          <span className="truncate text-[13px] font-bold text-[#B45309]">
            {formatActionValidationWaitingLabel(item.permission_hints?.can_validate === true)}
          </span>
        </div>
        <span className="shrink-0 text-[11px] text-[#E69138]">{relativeTimeLabel}</span>
      </div>

      <div className="my-2 border-t border-[#F0DFC8]" />

      <div className="mb-2 flex flex-wrap items-start gap-1.5">
        {showUrgentBadge ? <HoustonBadge variant="red">URGENT</HoustonBadge> : null}
        <SignalClassificationBadges signal={actionClassificationInput(item)} />
      </div>

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>

      {locationText ? (
        <p className="mt-1.5 text-[12px] text-[#888]">
          <span className="text-[#E24B4A]" aria-hidden>
            📍{' '}
          </span>
          {locationText}
        </p>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
            aria-hidden
          >
            {assigneeInitials}
          </div>
          <span className="truncate text-[11px] text-[#888]">{completedByLabel}</span>
        </div>
        <span className="shrink-0 text-[11px] font-semibold text-[#E69138]">Voir le détail →</span>
      </div>
    </article>
  )
}

function ClassicExecutionActionCard({ item, onSelect }: ExecutionActionCardProps) {
  const leftAccentColor = getActionCardLeftAccentColor(item.status)
  const showUrgentBadge = shouldShowActionUrgentBadge(item.signal_summary)
  const locationText = getActionLocationText(item.signal_summary)
  const creatorInitials = getDisplayNameInitials(item.created_by_display_name)
  const creatorLabel = formatActionCreatorFooterLabel(item.created_by_display_name)

  return (
    <article
      className={terrainFeedInteractiveCardClassName()}
      style={{ borderLeftColor: leftAccentColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="mb-2 flex flex-wrap items-start gap-1.5">
        {showUrgentBadge ? <HoustonBadge variant="red">URGENT</HoustonBadge> : null}
        <SignalClassificationBadges signal={actionClassificationInput(item)} />
      </div>

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>

      {locationText ? (
        <p className="mt-1.5 text-[12px] text-[#888]">
          <span className="text-[#E24B4A]" aria-hidden>
            📍{' '}
          </span>
          {locationText}
        </p>
      ) : null}

      {item.due_at ? (
        <div className="mt-3">
          <ActionDeadlineProgressBar
            createdAt={item.created_at}
            dueAt={item.due_at}
            isOverdue={item.is_overdue}
          />
        </div>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
            aria-hidden
          >
            {creatorInitials}
          </div>
          <span className="truncate text-[11px] text-[#888]">{creatorLabel}</span>
        </div>
        <ActionStatusBadge status={item.status} labelVariant="feed" className="shrink-0" />
      </div>
    </article>
  )
}

export function ExecutionActionCard({ item, onSelect }: ExecutionActionCardProps) {
  if (isActionPendingValidationCard(item)) {
    return <PendingValidationExecutionActionCard item={item} onSelect={onSelect} />
  }

  return <ClassicExecutionActionCard item={item} onSelect={onSelect} />
}
