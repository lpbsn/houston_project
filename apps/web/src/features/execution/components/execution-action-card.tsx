import { Bell } from 'lucide-react'
import type { KeyboardEvent } from 'react'

import type { ActionFeedItem } from '@/features/actions/types'
import { ActionStatusBadge } from '@/features/actions/components/action-status-badge'
import {
  formatActionCompletedByLabel,
  formatActionCreatorFooterLabel,
  formatActionDueByTimeLabel,
  formatActionRemainingTimeLabel,
  formatActionValidationRelativeTime,
  formatActionValidationWaitingLabel,
  getActionCardLeftAccentColor,
  getActionDeadlineRemainingPercent,
  getActionDomainBadgeLabel,
  getActionLocationText,
  getDisplayNameInitials,
  isActionDeadlineCritical,
  isActionPendingValidationCard,
  resolveActionValidationRelativeTimeIso,
  shouldShowActionUrgentBadge,
} from '@/features/actions/lib/action-display'
import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type ExecutionActionCardProps = {
  item: ActionFeedItem
  onSelect: (actionId: string) => void
}

function handleCardKeyDown(
  event: KeyboardEvent<HTMLElement>,
  onSelect: (actionId: string) => void,
  actionId: string,
) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onSelect(actionId)
  }
}

function PendingValidationExecutionActionCard({
  item,
  onSelect,
}: ExecutionActionCardProps) {
  const showUrgentBadge = shouldShowActionUrgentBadge(item.signal_summary)
  const domainLabel = getActionDomainBadgeLabel(item.domain_key)
  const locationText = getActionLocationText(item.signal_summary)
  const assigneeInitials = getDisplayNameInitials(item.assigned_to_display_name)
  const completedByLabel = formatActionCompletedByLabel(item.assigned_to_display_name)
  const relativeTimeLabel = formatActionValidationRelativeTime(
    resolveActionValidationRelativeTimeIso(item),
  )

  return (
    <article
      className={cn(
        'cursor-pointer rounded-[22px] border border-[#E69138] bg-[#FFF9ED] p-4 transition',
        'hover:border-[#E69138]/80',
      )}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => handleCardKeyDown(event, onSelect, item.id)}
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

      <div className="mb-2 flex flex-wrap gap-1">
        {showUrgentBadge ? <HoustonBadge variant="red">URGENT</HoustonBadge> : null}
        {domainLabel ? <HoustonBadge variant="gray">{domainLabel}</HoustonBadge> : null}
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
  const domainLabel = getActionDomainBadgeLabel(item.domain_key)
  const locationText = getActionLocationText(item.signal_summary)
  const deadlineRemainingPercent = getActionDeadlineRemainingPercent(item.created_at, item.due_at)
  const isDeadlineCritical = isActionDeadlineCritical({
    dueAt: item.due_at,
    isOverdue: item.is_overdue,
    createdAt: item.created_at,
  })
  const creatorInitials = getDisplayNameInitials(item.created_by_display_name)
  const creatorLabel = formatActionCreatorFooterLabel(item.created_by_display_name)

  return (
    <article
      className={cn(
        'cursor-pointer rounded-[22px] border border-[#E8E6DF] bg-white p-4',
        'border-l-4 transition',
        'hover:border-t-[#1B4FD8]/30 hover:border-r-[#1B4FD8]/30 hover:border-b-[#1B4FD8]/30',
      )}
      style={{ borderLeftColor: leftAccentColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => handleCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="mb-2 flex flex-wrap gap-1">
        {showUrgentBadge ? <HoustonBadge variant="red">URGENT</HoustonBadge> : null}
        {domainLabel ? <HoustonBadge variant="gray">{domainLabel}</HoustonBadge> : null}
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

      <div className="mt-3">
        <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
          <span
            className={cn(
              isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#666]',
            )}
          >
            {formatActionRemainingTimeLabel(item.due_at, item.is_overdue)}
          </span>
          {item.due_at ? (
            <span
              className={cn(
                'shrink-0',
                isDeadlineCritical ? 'font-medium text-[#B91C1C]' : 'text-[#888]',
              )}
            >
              {formatActionDueByTimeLabel(item.due_at)}
            </span>
          ) : null}
        </div>
        <div
          className="h-1 overflow-hidden rounded-full bg-[#F0EFE9]"
          role="progressbar"
          aria-valuenow={Math.round(deadlineRemainingPercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progression vers l'échéance"
        >
          <div
            className={cn(
              'h-full rounded-full transition-[width]',
              isDeadlineCritical ? 'bg-[#E24B4A]' : 'bg-[#1B4FD8]',
            )}
            style={{ width: `${deadlineRemainingPercent}%` }}
          />
        </div>
      </div>

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
