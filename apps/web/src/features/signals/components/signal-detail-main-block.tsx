import { MapPin } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { terrain, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatSignalRelativeTime,
  formatSignalSimilarObservationsLabel,
} from '../lib/signal-display'
import type { SignalDetail } from '../types'
import { SignalDetailPhotoSection } from './signal-detail-photo-section'
import { SignalStatusBadge } from './signal-status-badge'

type SignalDetailMainBlockProps = {
  signal: SignalDetail
  reporterName: string | null
  description: string
}

export function SignalDetailMainBlock({
  signal,
  reporterName,
  description,
}: SignalDetailMainBlockProps) {
  const location = signal.location_text?.trim() ?? ''
  const reporterInitials = reporterName ? getDisplayNameInitials(reporterName) : null
  const hasAggregation = signal.aggregation_count > 0
  const mediaItems = signal.media_items ?? []

  return (
    <TerrainCard className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <SignalStatusBadge status={signal.status} variant="detail" />
        <span className={cn('shrink-0 text-[12px]', terrain.textSecondary)}>
          {formatSignalRelativeTime(signal.last_activity_at)}
        </span>
      </div>

      <h2 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{signal.title}</h2>

      {reporterName ? (
        <div className="flex min-w-0 items-center gap-1.5">
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
          <span className={cn('truncate text-[12px]', terrain.textSecondary)}>
            Rapporté par {reporterName}
          </span>
        </div>
      ) : null}

      {location ? (
        <p
          className={cn('flex min-w-0 items-center gap-1 text-[12px]', terrain.textSecondary)}
        >
          <MapPin className="h-3 w-3 shrink-0 text-[#E24B4A]" aria-hidden />
          <span className="truncate">{location}</span>
        </p>
      ) : null}

      {hasAggregation ? (
        <p className={cn('text-[12px]', terrain.textSecondary)}>
          {formatSignalSimilarObservationsLabel(signal.aggregation_count)}
        </p>
      ) : null}

      <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{description}</p>

      {mediaItems.length > 0 ? (
        <SignalDetailPhotoSection mediaItems={mediaItems} tileSize="compact" embedded />
      ) : null}
    </TerrainCard>
  )
}
