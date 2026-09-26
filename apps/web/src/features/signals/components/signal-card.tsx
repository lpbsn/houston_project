import { MapPin, Pin } from 'lucide-react'

import { FeedCardActionsButton } from '@/components/domain/feed-card-meta-row'
import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { terrain, terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatSignalRelativeTime,
  formatSignalAggregationLabel,
  formatSignalFeedAggregationBadge,
  formatSignalFeedCardClassificationLine,
  formatSignalFeedPinnedPoleLabel,
  getPinnedSignalCardClassName,
  getSignalFeedInteractiveCardClassName,
  getSignalCardLeftAccentColor,
  getSignalCardSurfaceClass,
  PINNED_SIGNAL_CARD_BANNER_LABEL,
  PINNED_SIGNAL_CARD_DETAIL_CTA,
  PINNED_SIGNAL_CARD_SEPARATOR_CLASS,
} from '../lib/signal-display'
import { canOpenSignalFeedCardActions } from '../lib/signal-feed-card-actions'
import { isSignalMissingResponsibleClassification } from '../lib/signal-unclassified'
import type { SignalFeedItem, SignalViewMode } from '../types'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalUnclassifiedBadge } from './signal-unclassified-badge'

type SignalCardProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
  onOpenActions?: (item: SignalFeedItem) => void
  variant?: 'feed' | 'pinned'
  showEstablishment?: boolean
  viewMode?: SignalViewMode
  className?: string
}

function stopCardNavigation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

function SignalCardActionsButton({
  item,
  onOpenActions,
}: {
  item: SignalFeedItem
  onOpenActions: (item: SignalFeedItem) => void
}) {
  return (
    <FeedCardActionsButton
      ariaLabel="Actions de l'observation"
      variant="prominent"
      onClick={(event) => {
        stopCardNavigation(event)
        onOpenActions(item)
      }}
    />
  )
}

/** Secondary aggregation chip — muted Spore meta, not a primary brand badge. */
function SignalAggregationMeta({ count }: { count: number }) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 tabular-nums text-[11px] font-medium',
        terrain.textSecondary,
      )}
      aria-label={formatSignalAggregationLabel(count)}
    >
      {formatSignalFeedAggregationBadge(count)}
    </span>
  )
}

function FeedSignalCard({
  item,
  onSelect,
  onOpenActions,
  showEstablishment = false,
  viewMode = 'personal',
  className,
}: SignalCardProps) {
  const leftAccentColor = getSignalCardLeftAccentColor(item)
  const surfaceClass = getSignalCardSurfaceClass(item)
  const showActions =
    onOpenActions && canOpenSignalFeedCardActions(item.permission_hints)
  const classificationBadgeLabel = formatSignalFeedCardClassificationLine(item, viewMode)
  const showUnclassified = isSignalMissingResponsibleClassification(item)
  const location = item.location_text?.trim() ?? ''
  const establishmentName = item.establishment_name?.trim() ?? ''
  const validationRequested = item.resolution_request?.status === 'pending'
  const reporterName = item.reporter_display_name?.trim() ?? ''
  const reporterInitials = reporterName ? getDisplayNameInitials(reporterName) : null

  return (
    <article
      className={cn(getSignalFeedInteractiveCardClassName(surfaceClass), className)}
      style={{ borderLeftColor: leftAccentColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <SignalStatusBadge status={item.status} variant="feed" />
          {showUnclassified ? <SignalUnclassifiedBadge signal={item} variant="feed" /> : null}
          {!showUnclassified && classificationBadgeLabel ? (
            <HoustonBadge variant="gray">{classificationBadgeLabel}</HoustonBadge>
          ) : null}
          {validationRequested ? (
            <span className="rounded-full bg-[#EEF4FF] px-2 py-0.5 text-[10px] font-semibold text-[#355CA8]">
              Validation demandée
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <span className={cn('text-[11px] leading-none', terrain.textSecondary)}>
            {formatSignalRelativeTime(item.last_activity_at)}
          </span>
          {showActions ? (
            <SignalCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null}
        </div>
      </div>

      <h3 className="line-clamp-2 text-[15px] font-bold leading-snug text-[#1a1a1a]">
        {item.title}
      </h3>

      {reporterName ? (
        <div className="mt-1.5 flex min-w-0 items-center gap-1.5">
          {reporterInitials ? (
            <div
              className={cn(
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold',
                terrainFeedAvatar,
              )}
              aria-hidden
            >
              {reporterInitials}
            </div>
          ) : null}
          <span className={cn('truncate text-[11px]', terrain.textSecondary)}>
            Rapporté par {reporterName}
          </span>
        </div>
      ) : null}

      {showEstablishment && establishmentName ? (
        <span className="mt-1 inline-flex rounded-full bg-[#F0EFE9] px-2 py-0.5 text-[10px] font-semibold text-[#7D7B75]">
          {establishmentName}
        </span>
      ) : null}

      {location || item.aggregation_count > 0 ? (
        <div className="mt-1.5 flex items-center justify-between gap-3">
          {location ? (
            <p
              className={cn(
                'flex min-w-0 flex-1 items-center gap-1 text-[12px]',
                terrain.textSecondary,
              )}
            >
              <MapPin className="h-3 w-3 shrink-0 text-[#E24B4A]" aria-hidden />
              <span className="truncate">{location}</span>
            </p>
          ) : (
            <span />
          )}
          {item.aggregation_count > 0 ? (
            <SignalAggregationMeta count={item.aggregation_count} />
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

/** Highlight presentation for pinned items — importance marker, not a status card. */
function PinnedSignalCard({
  item,
  onSelect,
  onOpenActions,
  showEstablishment = false,
  className,
}: SignalCardProps) {
  const showActions =
    onOpenActions && canOpenSignalFeedCardActions(item.permission_hints)
  const poleLabel = formatSignalFeedPinnedPoleLabel(item)
  const showUnclassified = isSignalMissingResponsibleClassification(item)
  const location = item.location_text?.trim() ?? ''
  const establishmentName = item.establishment_name?.trim() ?? ''

  return (
    <article
      className={cn(getPinnedSignalCardClassName(), className)}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <Pin className={cn('h-3.5 w-3.5 shrink-0', terrain.muted)} aria-hidden />
          <span className={cn('text-[12px] font-semibold', terrain.muted)}>
            {PINNED_SIGNAL_CARD_BANNER_LABEL}
          </span>
          {showUnclassified ? <SignalUnclassifiedBadge signal={item} variant="feed" /> : null}
          {!showUnclassified && poleLabel ? (
            <HoustonBadge variant="gray">{poleLabel}</HoustonBadge>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <span className={cn('text-[11px] leading-none', terrain.textSecondary)}>
            {formatSignalRelativeTime(item.last_activity_at)}
          </span>
          {showActions ? (
            <SignalCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null}
        </div>
      </div>

      <div className={`my-2 ${PINNED_SIGNAL_CARD_SEPARATOR_CLASS}`} />

      <h3 className="line-clamp-2 text-[15px] font-semibold leading-snug text-[#1a1a1a]">
        {item.title}
      </h3>

      {showEstablishment && establishmentName ? (
        <span className="mt-1 inline-flex rounded-full bg-[#F0EFE9] px-2 py-0.5 text-[10px] font-semibold text-[#7D7B75]">
          {establishmentName}
        </span>
      ) : null}

      {location ? (
        <p
          className={cn(
            'mt-1.5 flex min-w-0 items-center gap-1 text-[12px]',
            terrain.textSecondary,
          )}
        >
          <MapPin className="h-3 w-3 shrink-0 text-[#E24B4A]" aria-hidden />
          <span className="truncate">{location}</span>
        </p>
      ) : null}

      <div className="mt-3 flex items-center justify-end">
        <span className={cn('shrink-0 text-[11px] font-semibold', terrainBrandAction.text)}>
          {PINNED_SIGNAL_CARD_DETAIL_CTA}
        </span>
      </div>
    </article>
  )
}

export function SignalCard({
  item,
  onSelect,
  onOpenActions,
  variant = 'feed',
  showEstablishment = false,
  viewMode = 'personal',
  className,
}: SignalCardProps) {
  if (variant === 'pinned') {
    return (
      <PinnedSignalCard
        item={item}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        showEstablishment={showEstablishment}
        viewMode={viewMode}
        className={className}
      />
    )
  }

  return (
    <FeedSignalCard
      item={item}
      onSelect={onSelect}
      onOpenActions={onOpenActions}
      showEstablishment={showEstablishment}
      viewMode={viewMode}
      className={className}
    />
  )
}
