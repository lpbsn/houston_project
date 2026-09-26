import { Pin } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'
import { ActionPlanPinnedBadge } from '@/features/action-plans/components/action-plan-pinned-badge'
import { getActionPlanStatusBadgeVariant } from '@/features/action-plans/components/action-plan-status-badge'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  formatActionPlanFeedCardDateTimeLabel,
  formatActionPlanFeedCardDelayLabel,
  formatActionPlanFeedCardStatusLabel,
  formatActionPlanFeedMarkedDoneLine,
  formatActionPlanFeedOtherPolesCountLabel,
  formatActionPlanFeedTerminalDateLabel,
  formatActionPlanFeedValidatedLine,
  formatExecutionFeedCreatedLabel,
  getActionPlanFeedOtherPoles,
} from '../lib/action-plan-execution-feed-card-display'
import { useFeedCardNow } from '../lib/use-feed-card-now'
import {
  ExecutionFeedDelayChip,
  ExecutionFeedReviewStars,
} from './execution-feed-status-bits'

type ActionPlanExecutionFeedDesktopRowProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
  onTogglePin?: (item: ActionPlanExecutionFeedItem) => void
}

function stopRowActivation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

function DesktopPinButton({
  item,
  onTogglePin,
}: {
  item: ActionPlanExecutionFeedItem
  onTogglePin: (item: ActionPlanExecutionFeedItem) => void
}) {
  if (!item.permission_hints.can_pin) {
    return null
  }
  return (
    <button
      type="button"
      className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#5F5A52]',
        'hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
      )}
      aria-label={item.is_pinned ? 'Désépingler' : 'Épingler'}
      aria-pressed={item.is_pinned}
      onClick={(event) => {
        stopRowActivation(event)
        onTogglePin(item)
      }}
    >
      <Pin
        className={cn('h-4 w-4', item.is_pinned && 'fill-current text-[#1a1a1a]')}
        aria-hidden
      />
    </button>
  )
}

function DebutFinLine({
  item,
}: {
  item: Pick<ActionPlanExecutionFeedItem, 'start_at' | 'end_at' | 'all_day'>
}) {
  const startLabel = formatActionPlanFeedCardDateTimeLabel(item.start_at, item.all_day)
  const endLabel = formatActionPlanFeedCardDateTimeLabel(item.end_at, item.all_day)
  if (!startLabel && !endLabel && !item.all_day) {
    return null
  }
  return (
    <span className="flex flex-col gap-0.5 text-[12px] leading-snug text-[#5c564e]">
      {startLabel || endLabel ? (
        <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          {startLabel ? (
            <span className="min-w-0">
              <span className="text-[#9a958c]">Début</span> {startLabel}
            </span>
          ) : null}
          {endLabel ? (
            <span className="min-w-0">
              <span className="text-[#9a958c]">Fin</span> {endLabel}
            </span>
          ) : null}
        </span>
      ) : null}
      {item.all_day && !startLabel && !endLabel ? (
        <span className="text-[#9a958c]">Journée entière</span>
      ) : null}
    </span>
  )
}

export function ActionPlanExecutionFeedDesktopRow({
  item,
  onSelect,
  onTogglePin,
}: ActionPlanExecutionFeedDesktopRowProps) {
  const now = useFeedCardNow()
  const delayLabel = formatActionPlanFeedCardDelayLabel(item.end_at, now, item.is_overdue)
  const statusLabel = formatActionPlanFeedCardStatusLabel(item)
  const otherPoles = getActionPlanFeedOtherPoles(item)
  const validatedLine =
    item.status === 'done' && item.validated_at != null
      ? formatActionPlanFeedValidatedLine(item)
      : null
  const canceledLine =
    item.status === 'canceled' ? formatActionPlanFeedTerminalDateLabel(item) : null
  const markedDoneLine =
    item.status === 'pending_validation' ? formatActionPlanFeedMarkedDoneLine(item) : null
  const reviewStars =
    item.status === 'done' && item.validated_at != null && item.active_review != null
      ? item.active_review.stars
      : null
  const terminalStatusLine = validatedLine ?? canceledLine
  const createdLabel = terminalStatusLine
    ? null
    : formatExecutionFeedCreatedLabel(item.created_at)
  const creatorName = item.created_by_display_name.trim()
  const poleLabel = item.pilot_business_unit.specific_name.trim()
  const assignees = item.assignees.filter((assignee) => assignee.display_name.trim().length > 0)
  const showReadOnlyPinnedBadge = !onTogglePin && item.is_pinned
  const showCreatedOrDelay = Boolean(createdLabel || delayLabel)

  return (
    <article className="flex flex-col gap-0 rounded-xl border border-[#E8E6DF] bg-white px-3 py-2.5">
      <div className="flex items-start gap-2">
        <button
          type="button"
          className="min-w-0 flex-1 rounded-lg px-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
          onClick={() => onSelect(item.id)}
        >
          <h3 className="break-words text-[15px] font-semibold leading-snug text-[#1a1a1a]">
            {item.title}
          </h3>
        </button>
        {onTogglePin ? <DesktopPinButton item={item} onTogglePin={onTogglePin} /> : null}
      </div>
      <button
        type="button"
        className="flex flex-col gap-2 rounded-lg px-1 py-0.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
        onClick={() => onSelect(item.id)}
      >
        <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          {showReadOnlyPinnedBadge ? <ActionPlanPinnedBadge /> : null}
          <HoustonBadge variant={getActionPlanStatusBadgeVariant(item.status)}>
            {statusLabel}
          </HoustonBadge>
          {poleLabel ? (
            <HoustonBadge variant="gray" className="max-w-full leading-none break-words">
              {poleLabel}
            </HoustonBadge>
          ) : null}
          {otherPoles.otherCount > 0 ? (
            <HoustonBadge variant="gray" className="shrink-0 leading-none">
              {formatActionPlanFeedOtherPolesCountLabel(otherPoles.otherCount)}
            </HoustonBadge>
          ) : null}
        </span>
        <DebutFinLine item={item} />
        {assignees.length > 0 ? (
          <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
            {assignees.map((assignee) => (
              <span
                key={assignee.membership_id}
                className="inline-flex max-w-full items-center gap-1.5"
              >
                <span
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
                  aria-hidden
                >
                  {getDisplayNameInitials(assignee.display_name)}
                </span>
                <span className="break-words text-[12px] leading-snug text-[#5c564e]">
                  {assignee.display_name}
                </span>
              </span>
            ))}
          </span>
        ) : null}
        {terminalStatusLine ? (
          <span className="text-[11px] leading-snug text-[#9a958c]">{terminalStatusLine}</span>
        ) : null}
        {reviewStars != null ? <ExecutionFeedReviewStars stars={reviewStars} /> : null}
        {markedDoneLine ? (
          <span className="text-[11px] leading-snug text-[#9a958c]">{markedDoneLine}</span>
        ) : null}
        {showCreatedOrDelay ? (
          <span className="flex min-w-0 items-center justify-between gap-2 text-[11px] leading-snug text-[#9a958c]">
            <span className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1">
              {createdLabel ? (
                <>
                  <span>{createdLabel}</span>
                  {creatorName ? (
                    <>
                      <span>par</span>
                      <span className="inline-flex max-w-full items-center gap-1.5">
                        <span
                          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-[9px] font-bold text-[#5c564e]"
                          aria-hidden
                        >
                          {getDisplayNameInitials(creatorName)}
                        </span>
                        <span className="break-words">{creatorName}</span>
                      </span>
                    </>
                  ) : null}
                </>
              ) : (
                <span />
              )}
            </span>
            {delayLabel ? <ExecutionFeedDelayChip label={delayLabel} /> : null}
          </span>
        ) : null}
      </button>
    </article>
  )
}
