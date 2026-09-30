import { MapPin } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
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
  const hasAggregation = signal.aggregation_count > 0
  const mediaItems = signal.media_items ?? []
  const contextMeta = [
    reporterName ? `Rapporté par ${reporterName}` : null,
    formatSignalRelativeTime(signal.last_activity_at),
    hasAggregation ? formatSignalSimilarObservationsLabel(signal.aggregation_count) : null,
  ]
    .filter((part): part is string => part != null)
    .join(' · ')

  return (
    <TerrainCard className="flex flex-col gap-2.5">
      <SignalStatusBadge status={signal.status} variant="feed" className="w-fit self-start" />

      <h1 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{signal.title}</h1>

      {location ? (
        <p className="flex min-w-0 items-start gap-1.5 text-[13px] font-medium leading-snug text-[#1a1a1a]">
          <MapPin className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', terrain.danger)} aria-hidden />
          <span className="min-w-0">{location}</span>
        </p>
      ) : null}

      <p className={cn('text-[11px] leading-snug', terrain.muted)}>{contextMeta}</p>

      <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{description}</p>

      {mediaItems.length > 0 ? (
        <SignalDetailPhotoSection mediaItems={mediaItems} tileSize="compact" embedded />
      ) : null}
    </TerrainCard>
  )
}
