import type { KeyboardEvent } from 'react'

import { getDisplayNameInitials } from '@/features/actions/lib/action-display'
import { terrainFeedInteractiveCardClassName } from '@/lib/terrain-styles'

import {
  formatSignalRelativeTime,
  getSignalCardLeftAccentColor,
  getSignalCardSurfaceClass,
} from '../lib/signal-display'
import type { SignalFeedItem } from '../types'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalTaxonomyBadges } from './signal-taxonomy-badges'
import { SignalUrgencyBadge } from './signal-urgency-badge'

type SignalCardProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
}

function handleCardKeyDown(
  event: KeyboardEvent<HTMLElement>,
  onSelect: (signalId: string) => void,
  signalId: string,
) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onSelect(signalId)
  }
}

export function SignalCard({ item, onSelect }: SignalCardProps) {
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
      onKeyDown={(event) => handleCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          <SignalUrgencyBadge urgency={item.urgency} />
          <SignalTaxonomyBadges
            domainKey={item.domain_key}
            subjectKey={item.subject_key}
            moduleKey={item.module_key}
            compact
          />
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
            {reporterName ? <span className="truncate">{reporterName}</span> : null}
            {item.is_pinned ? (
              <span className="shrink-0 font-medium text-[#1B4FD8]">Épinglé</span>
            ) : reporterName ? null : (
              '\u00a0'
            )}
          </span>
        </div>
        <SignalStatusBadge status={item.status} variant="feed" />
      </div>
    </article>
  )
}
