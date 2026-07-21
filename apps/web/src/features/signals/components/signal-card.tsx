import { MapPin, Pin } from 'lucide-react'

import { FeedCardActionsButton, FeedCardMetaRow } from '@/components/domain/feed-card-meta-row'
import { getDisplayNameInitials } from '@/lib/display-names'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatSignalRelativeTime,
  formatSignalAggregationBadge,
  formatSignalAggregationLabel,
  getPinnedSignalCardClassName,
  getSignalFeedInteractiveCardClassName,
  PINNED_SIGNAL_CARD_BANNER_LABEL,
  PINNED_SIGNAL_CARD_DETAIL_CTA,
  PINNED_SIGNAL_CARD_SEPARATOR_CLASS,
  getSignalCardLeftAccentColor,
  getSignalCardSurfaceClass,
} from '../lib/signal-display'
import { canOpenSignalFeedCardActions } from '../lib/signal-feed-card-actions'
import type { SignalFeedItem } from '../types'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalClassificationBadges } from './signal-classification-badges'

type SignalCardProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
  onOpenActions?: (item: SignalFeedItem) => void
  variant?: 'feed' | 'pinned'
}

function stopCardNavigation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

type SignalCardActionsButtonProps = {
  item: SignalFeedItem
  onOpenActions: (item: SignalFeedItem) => void
}

function SignalCardActionsButton({ item, onOpenActions }: SignalCardActionsButtonProps) {
  return (
    <FeedCardActionsButton
      ariaLabel="Actions de l'observation"
      onClick={(event) => {
        stopCardNavigation(event)
        onOpenActions(item)
      }}
    />
  )
}

type SignalAggregationBadgeProps = {
  count: number
}

function SignalAggregationBadge({ count }: SignalAggregationBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-bold text-white tabular-nums',
        terrainBrandAction.bg,
      )}
      aria-label={formatSignalAggregationLabel(count)}
    >
      {formatSignalAggregationBadge(count)}
    </span>
  )
}

function SignalLocationRow({
  locationText,
  aggregationCount,
}: {
  locationText: string
  aggregationCount: number
}) {
  return (
    <div className="mt-1.5 flex items-center justify-between gap-3">
      <p className="flex min-w-0 flex-1 items-center gap-1 text-[12px] text-[#888]">
        <MapPin className="h-3 w-3 shrink-0 text-[#E24B4A]" aria-hidden />
        <span className="truncate">{locationText}</span>
      </p>
      {aggregationCount > 0 ? <SignalAggregationBadge count={aggregationCount} /> : null}
    </div>
  )
}

function SignalAggregationRow({ aggregationCount }: { aggregationCount: number }) {
  return (
    <div className="mt-1.5 flex justify-end">
      <SignalAggregationBadge count={aggregationCount} />
    </div>
  )
}

function FeedSignalCard({ item, onSelect, onOpenActions }: SignalCardProps) {
  const leftAccentColor = getSignalCardLeftAccentColor(item)
  const surfaceClass = getSignalCardSurfaceClass(item)
  const reporterName = item.reporter_display_name?.trim() ?? ''
  const reporterInitials = reporterName ? getDisplayNameInitials(reporterName) : null
  const showActions =
    onOpenActions && canOpenSignalFeedCardActions(item.permission_hints)

  return (
    <article
      className={getSignalFeedInteractiveCardClassName(surfaceClass)}
      style={{ borderLeftColor: leftAccentColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <FeedCardMetaRow
        timeLabel={formatSignalRelativeTime(item.last_activity_at)}
        badges={<SignalClassificationBadges signal={item} />}
        actions={
          showActions ? (
            <SignalCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null
        }
      />

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>
      {item.location_text ? (
        <SignalLocationRow
          locationText={item.location_text}
          aggregationCount={item.aggregation_count}
        />
      ) : item.aggregation_count > 0 ? (
        <SignalAggregationRow aggregationCount={item.aggregation_count} />
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
        <div className="flex min-w-0 items-center gap-2">
          {reporterInitials ? (
            <div
              className={cn(
                'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                terrainFeedAvatar,
              )}
              aria-hidden
            >
              {reporterInitials}
            </div>
          ) : null}
          {reporterName ? (
            <span className="truncate text-[11px] text-[#888]">{reporterName}</span>
          ) : null}
        </div>
        <SignalStatusBadge status={item.status} variant="feed" />
      </div>
    </article>
  )
}

function PinnedSignalCard({ item, onSelect, onOpenActions }: SignalCardProps) {
  const showActions =
    onOpenActions && canOpenSignalFeedCardActions(item.permission_hints)

  return (
    <article
      className={getPinnedSignalCardClassName()}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Pin className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
          <span className={cn('truncate text-[13px] font-bold', terrainBrandAction.text)}>
            {PINNED_SIGNAL_CARD_BANNER_LABEL}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <span className="text-[11px] leading-none text-[#888]">
            {formatSignalRelativeTime(item.last_activity_at)}
          </span>
          {showActions ? (
            <SignalCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null}
        </div>
      </div>

      <div className={`my-2 ${PINNED_SIGNAL_CARD_SEPARATOR_CLASS}`} />

      <div className="mb-1 flex flex-wrap items-center gap-1">
        <SignalClassificationBadges signal={item} />
      </div>

      <h3 className="line-clamp-2 text-[15px] font-semibold leading-snug text-[#1a1a1a]">
        {item.title}
      </h3>

      {item.location_text ? (
        <SignalLocationRow locationText={item.location_text} aggregationCount={0} />
      ) : null}

      <div className="mt-3 flex items-center justify-end">
        <span className={cn('shrink-0 text-[11px] font-semibold', terrainBrandAction.text)}>
          {PINNED_SIGNAL_CARD_DETAIL_CTA}
        </span>
      </div>
    </article>
  )
}

export function SignalCard({ item, onSelect, onOpenActions, variant = 'feed' }: SignalCardProps) {
  if (variant === 'pinned') {
    return <PinnedSignalCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
  }
  return <FeedSignalCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
}
