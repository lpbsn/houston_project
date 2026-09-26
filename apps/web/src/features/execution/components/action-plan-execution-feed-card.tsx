import type { ReactNode } from 'react'
import { Bell, Pin } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'
import { getActionPlanStatusBadgeVariant } from '@/features/action-plans/components/action-plan-status-badge'
import { actionPlanBusinessUnitPrimaryLabel } from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { useFeedCardNow } from '../lib/use-feed-card-now'
import {
  computeTemporalProgressPercent,
  formatActionPlanFeedCardAssigneeDisplay,
  formatActionPlanFeedCardDateTimeLabel,
  formatActionPlanFeedCardDelayLabel,
  formatActionPlanFeedCardStatusLabel,
  formatActionPlanFeedMarkedDoneLine,
  formatActionPlanFeedOtherPolesCountLabel,
  formatActionPlanFeedStartsInLabel,
  formatActionPlanFeedTerminalDateLabel,
  formatActionPlanFeedValidatedLine,
  getActionPlanFeedOtherPoles,
} from '../lib/action-plan-execution-feed-card-display'
import {
  ExecutionFeedDelayChip,
  ExecutionFeedReviewStars,
} from './execution-feed-status-bits'

type ActionPlanExecutionFeedCardProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
  onTogglePin?: (item: ActionPlanExecutionFeedItem) => void
  className?: string
}

function stopCardNavigation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

function FeedPinButton({
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
      className="-my-2.5 -mr-1 inline-flex min-h-12 min-w-12 shrink-0 items-center justify-center rounded-lg text-[#7D7B75] transition active:opacity-80"
      aria-label={item.is_pinned ? 'Désépingler' : 'Épingler'}
      aria-pressed={item.is_pinned}
      onClick={(event) => {
        stopCardNavigation(event)
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

function TemporalProgressBar({ percent }: { percent: number }) {
  const clamped = Math.min(100, Math.max(0, percent))
  const fillWidth = clamped + '%'
  const knobLeft = 'calc(' + String(clamped) + '% - 5px)'
  return (
    <div
      className="relative mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[#EFEDE7]"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Progression temporelle"
    >
      <div className={cn('h-full rounded-full', terrainBrandAction.bg)} style={{ width: fillWidth }} />
      <span
        className={cn(
          'absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-white',
          terrainBrandAction.bg,
        )}
        style={{ left: knobLeft }}
        aria-hidden
      />
    </div>
  )
}

function AssigneesRow({ item }: { item: ActionPlanExecutionFeedItem }) {
  const { visible, overflow, empty } = formatActionPlanFeedCardAssigneeDisplay(item.assignees)
  if (empty) {
    return <p className="text-xs text-[#7D7B75]">Non assigné</p>
  }
  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="flex shrink-0 -space-x-1.5">
        {visible.map((name) => (
          <span
            key={name}
            className={cn(
              terrainFeedAvatar,
              'inline-flex h-6 w-6 items-center justify-center rounded-full border border-white text-[10px] font-semibold',
            )}
            aria-hidden
          >
            {getDisplayNameInitials(name)}
          </span>
        ))}
      </div>
      <p className="min-w-0 truncate text-xs text-[#3d3d3d]">
        {visible.join(', ')}
        {overflow > 0 ? ` +${overflow}` : ''}
      </p>
    </div>
  )
}

function CreatorLine({ name }: { name: string }) {
  const trimmed = name.trim()
  if (!trimmed) {
    return null
  }
  return <p className="text-xs text-[#7D7B75]">Créé par {trimmed}</p>
}

function PoleHeader({
  item,
  statusTone,
  showBell,
  onTogglePin,
}: {
  item: ActionPlanExecutionFeedItem
  statusTone?: string
  showBell?: boolean
  onTogglePin?: (item: ActionPlanExecutionFeedItem) => void
}) {
  const other = getActionPlanFeedOtherPoles(item)
  return (
    <div className="flex items-center gap-2">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
        <HoustonBadge
          variant={getActionPlanStatusBadgeVariant(item.status)}
          className={cn('max-w-full truncate', statusTone)}
          aria-label={formatActionPlanFeedCardStatusLabel(item)}
        >
          {showBell ? <Bell className="mr-1 h-3 w-3" aria-hidden /> : null}
          {formatActionPlanFeedCardStatusLabel(item)}
        </HoustonBadge>
        <HoustonBadge variant="gray" className="max-w-[9rem] truncate">
          {actionPlanBusinessUnitPrimaryLabel(item.pilot_business_unit)}
        </HoustonBadge>
        {other.otherCount > 0 ? (
          <HoustonBadge variant="gray" className="shrink-0">
            {formatActionPlanFeedOtherPolesCountLabel(other.otherCount)}
          </HoustonBadge>
        ) : null}
      </div>
      {onTogglePin ? <FeedPinButton item={item} onTogglePin={onTogglePin} /> : null}
    </div>
  )
}

function OtherPolesLine({ item }: { item: ActionPlanExecutionFeedItem }) {
  const other = getActionPlanFeedOtherPoles(item)
  if (other.otherCount === 0) {
    return null
  }
  const named = other.names.join(' · ')
  const suffix = other.overflow > 0 ? ` +${other.overflow}` : ''
  return (
    <p className="text-xs text-[#7D7B75]">
      Avec {named}
      {suffix}
    </p>
  )
}

function CardShell({
  item,
  onSelect,
  className,
  surfaceClassName,
  children,
}: {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
  className?: string
  surfaceClassName?: string
  children: ReactNode
}) {
  return (
    <article
      role="button"
      tabIndex={0}
      className={cn(
        'rounded-[14px] border border-[#E8E6DF] bg-white p-3 text-left transition active:opacity-95',
        surfaceClassName,
        className,
      )}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      aria-label={item.title}
    >
      {children}
    </article>
  )
}

function CardTitle({ title }: { title: string }) {
  return (
    <h3 className="mt-0.5 line-clamp-2 text-[15px] font-semibold leading-snug text-[#1a1a1a]">
      {title}
    </h3>
  )
}

function InProgressCard({
  item,
  onSelect,
  onTogglePin,
  className,
}: ActionPlanExecutionFeedCardProps) {
  const now = useFeedCardNow()
  const startLabel = formatActionPlanFeedCardDateTimeLabel(item.start_at, item.all_day)
  const endLabel = formatActionPlanFeedCardDateTimeLabel(item.end_at, item.all_day)
  const delayLabel = formatActionPlanFeedCardDelayLabel(item.end_at, now, item.is_overdue)
  const progress =
    item.all_day || !item.start_at || !item.end_at
      ? null
      : computeTemporalProgressPercent(item.start_at, item.end_at, now)

  return (
    <CardShell item={item} onSelect={onSelect} className={className}>
      <PoleHeader item={item} onTogglePin={onTogglePin} />
      <CardTitle title={item.title} />
      <OtherPolesLine item={item} />
      {(startLabel || endLabel || progress != null || item.all_day) && (
        <div className="mt-2">
          {(startLabel || endLabel) && (
            <div className="flex items-baseline justify-between gap-2 text-xs text-[#3d3d3d]">
              <span className="min-w-0 truncate">
                {startLabel ? (
                  <>
                    <span className="text-[#7D7B75]">Début</span> {startLabel}
                  </>
                ) : null}
              </span>
              <span className="min-w-0 shrink-0 text-right">
                {endLabel ? (
                  <>
                    <span className="text-[#7D7B75]">Fin</span> {endLabel}
                  </>
                ) : null}
              </span>
            </div>
          )}
          {item.all_day && progress == null ? (
            <p className="text-xs text-[#7D7B75]">Journée entière</p>
          ) : null}
          {progress != null ? (
            <TemporalProgressBar percent={item.is_overdue ? 100 : progress} />
          ) : null}
        </div>
      )}
      <div className="mt-3 space-y-1">
        <AssigneesRow item={item} />
        <div className="flex min-w-0 items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <CreatorLine name={item.created_by_display_name} />
          </div>
          {delayLabel ? <ExecutionFeedDelayChip label={delayLabel} /> : null}
        </div>
      </div>
    </CardShell>
  )
}

function PendingValidationCard({
  item,
  onSelect,
  onTogglePin,
  className,
}: ActionPlanExecutionFeedCardProps) {
  const endLabel = formatActionPlanFeedCardDateTimeLabel(item.end_at, item.all_day)
  const markedDoneLine = formatActionPlanFeedMarkedDoneLine(item)
  return (
    <CardShell
      item={item}
      onSelect={onSelect}
      className={className}
      surfaceClassName="border-[#F3E6D4] bg-[#FFFBF5]"
    >
      <PoleHeader
        item={item}
        statusTone="bg-[#F5E6C8] text-[#8A5A12]"
        showBell
        onTogglePin={onTogglePin}
      />
      <CardTitle title={item.title} />
      <OtherPolesLine item={item} />
      {endLabel ? (
        <p className="mt-2 text-xs text-[#3d3d3d]">
          <span className="text-[#7D7B75]">Fin prévue</span> {endLabel}
        </p>
      ) : null}
      {markedDoneLine ? <p className="mt-1.5 text-xs text-[#7D7B75]">{markedDoneLine}</p> : null}
      <div className="mt-3 space-y-1">
        <AssigneesRow item={item} />
        <CreatorLine name={item.created_by_display_name} />
      </div>
    </CardShell>
  )
}

function ScheduledCard({
  item,
  onSelect,
  onTogglePin,
  className,
}: ActionPlanExecutionFeedCardProps) {
  const now = useFeedCardNow()
  const startLabel = formatActionPlanFeedCardDateTimeLabel(item.start_at, item.all_day)
  const endLabel = formatActionPlanFeedCardDateTimeLabel(item.end_at, item.all_day)
  const startsIn = formatActionPlanFeedStartsInLabel(item.start_at, now)
  const progress =
    item.all_day || !item.visible_from || !item.start_at
      ? null
      : computeTemporalProgressPercent(item.visible_from, item.start_at, now)

  return (
    <CardShell item={item} onSelect={onSelect} className={className}>
      <PoleHeader item={item} onTogglePin={onTogglePin} />
      <CardTitle title={item.title} />
      <OtherPolesLine item={item} />
      <div className="mt-2 space-y-0.5 text-xs text-[#3d3d3d]">
        {(startLabel || endLabel) && (
          <div className="flex items-baseline justify-between gap-2">
            <span className="min-w-0 truncate">
              {startLabel ? (
                <>
                  <span className="text-[#7D7B75]">Début</span> {startLabel}
                </>
              ) : null}
            </span>
            <span className="min-w-0 shrink-0 text-right">
              {endLabel ? (
                <>
                  <span className="text-[#7D7B75]">Fin</span> {endLabel}
                </>
              ) : null}
            </span>
          </div>
        )}
        {startsIn ? <p className="text-[#7D7B75]">{startsIn}</p> : null}
      </div>
      {progress != null ? <TemporalProgressBar percent={progress} /> : null}
      <div className="mt-3 space-y-1">
        <AssigneesRow item={item} />
        <CreatorLine name={item.created_by_display_name} />
      </div>
    </CardShell>
  )
}

function TerminalCard({
  item,
  onSelect,
  onTogglePin,
  className,
}: ActionPlanExecutionFeedCardProps) {
  const validatedLine =
    item.status === 'done' && item.validated_at
      ? formatActionPlanFeedValidatedLine(item)
      : null
  const dateLabel =
    validatedLine ?? formatActionPlanFeedTerminalDateLabel(item)
  const reviewStars =
    item.status === 'done' && item.validated_at != null && item.active_review != null
      ? item.active_review.stars
      : null
  const muted = item.status === 'canceled'
  return (
    <CardShell
      item={item}
      onSelect={onSelect}
      className={className}
      surfaceClassName={muted ? 'bg-[#FAFAF8]' : undefined}
    >
      <PoleHeader item={item} onTogglePin={onTogglePin} />
      <CardTitle title={item.title} />
      {dateLabel ? <p className="mt-1.5 text-xs text-[#7D7B75]">{dateLabel}</p> : null}
      {reviewStars != null ? <ExecutionFeedReviewStars stars={reviewStars} /> : null}
      <div className="mt-2">
        <AssigneesRow item={item} />
      </div>
    </CardShell>
  )
}

export function ActionPlanExecutionFeedCard({
  item,
  onSelect,
  onTogglePin,
  className,
}: ActionPlanExecutionFeedCardProps) {
  switch (item.status) {
    case 'pending_validation':
      return (
        <PendingValidationCard
          item={item}
          onSelect={onSelect}
          onTogglePin={onTogglePin}
          className={className}
        />
      )
    case 'scheduled':
      return (
        <ScheduledCard
          item={item}
          onSelect={onSelect}
          onTogglePin={onTogglePin}
          className={className}
        />
      )
    case 'done':
    case 'canceled':
      return (
        <TerminalCard
          item={item}
          onSelect={onSelect}
          onTogglePin={onTogglePin}
          className={className}
        />
      )
    case 'in_progress':
    default:
      return (
        <InProgressCard
          item={item}
          onSelect={onSelect}
          onTogglePin={onTogglePin}
          className={className}
        />
      )
  }
}
