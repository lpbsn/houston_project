import { Pin } from 'lucide-react'

import { getDisplayNameInitials } from '@/features/actions/lib/action-display'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { terrainFeedCardBaseClassName, terrainFeedInteractiveCardClassName } from '@/lib/terrain-styles'

import {
  formatSignalRelativeTime,
  getPinnedSignalCardClassName,
  PINNED_SIGNAL_CARD_BANNER_LABEL,
  PINNED_SIGNAL_CARD_DETAIL_CTA,
  PINNED_SIGNAL_CARD_SEPARATOR_CLASS,
  getSignalCardLeftAccentColor,
  getSignalCardSurfaceClass,
} from '../lib/signal-display'
import type { SignalFeedItem } from '../types'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalClassificationBadges } from './signal-classification-badges'
import { SignalUrgencyBadge } from './signal-urgency-badge'

type SignalCardProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
  variant?: 'feed' | 'pinned'
}

function FeedSignalCard({ item, onSelect }: SignalCardProps) {
  const leftAccentColor = getSignalCardLeftAccentColor(item)
  const surfaceClass = getSignalCardSurfaceClass(item)
  const reporterName = item.reporter_display_name?.trim() ?? ''
  const reporterInitials = reporterName
    ? getDisplayNameInitials(reporterName)
    : null

  return (
    <article
      className={terrainFeedInteractiveCardClassName(surfaceClass)}
      style={{ borderLeftColor: leftAccentColor }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          <SignalUrgencyBadge urgency={item.urgency} />
          <SignalClassificationBadges signal={item} />
        </div>
        <span className="shrink-0 text-[11px] text-[#888]">
          {formatSignalRelativeTime(item.last_activity_at)}
        </span>
      </div>

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>

      {item.location_text ? (
        <p className="mt-1.5 text-[12px] text-[#888]">
          <span className="text-[#E24B4A]" aria-hidden>
            📍{' '}
          </span>
          {item.location_text}
        </p>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
        <div className="flex min-w-0 items-center gap-2">
          {reporterInitials ? (
            <div
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
              aria-hidden
            >
              {reporterInitials}
            </div>
          ) : null}
          <span className="flex min-w-0 items-center gap-2 truncate text-[11px] text-[#888]">
            {reporterName ? <span className="truncate">{reporterName}</span> : '\u00a0'}
          </span>
        </div>
        <SignalStatusBadge status={item.status} variant="feed" />
      </div>
    </article>
  )
}

function PinnedSignalCard({ item, onSelect }: SignalCardProps) {
  return (
    <article
      className={terrainFeedCardBaseClassName(getPinnedSignalCardClassName())}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Pin className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
          <span className="truncate text-[13px] font-bold text-[#555]">
            {PINNED_SIGNAL_CARD_BANNER_LABEL}
          </span>
        </div>
        <span className="shrink-0 text-[11px] text-[#888]">
          {formatSignalRelativeTime(item.last_activity_at)}
        </span>
      </div>

      <div className={`my-2 ${PINNED_SIGNAL_CARD_SEPARATOR_CLASS}`} />

      <div className="mb-2 flex flex-wrap gap-1">
        <SignalUrgencyBadge urgency={item.urgency} />
        <SignalClassificationBadges signal={item} />
      </div>

      <h3 className="line-clamp-2 text-[15px] font-semibold leading-snug text-[#1a1a1a]">
        {item.title}
      </h3>

      {item.location_text ? (
        <p className="mt-1.5 text-[12px] text-[#888]">
          <span className="text-[#7D7B75]" aria-hidden>
            📍{' '}
          </span>
          {item.location_text}
        </p>
      ) : null}

      <div className="mt-3 flex items-center justify-end">
        <span className="shrink-0 text-[11px] font-semibold text-[#7D7B75]">
          {PINNED_SIGNAL_CARD_DETAIL_CTA}
        </span>
      </div>
    </article>
  )
}

export function SignalCard({ item, onSelect, variant = 'feed' }: SignalCardProps) {
  if (variant === 'pinned') {
    return <PinnedSignalCard item={item} onSelect={onSelect} />
  }
  return <FeedSignalCard item={item} onSelect={onSelect} />
}
