import { motion, useReducedMotion } from 'framer-motion'

import { terrainTapProps } from '@/lib/terrain-motion'
import { cn } from '@/lib/utils'

import {
  formatSignalRelativeTime,
  getSignalCardLeftAccentClass,
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

export function SignalCard({ item, onSelect }: SignalCardProps) {
  const shouldReduceMotion = useReducedMotion()
  const leftAccent = getSignalCardLeftAccentClass(item)
  const surfaceClass = getSignalCardSurfaceClass(item)

  const card = (
    <article
      className={cn(
        'cursor-pointer rounded-[14px] border border-[#E8E6DF] bg-white py-3 pl-3 pr-3.5',
        'border-l-4 transition hover:border-[#1B4FD8]/30',
        leftAccent,
        surfaceClass,
      )}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(item.id)
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          <SignalUrgencyBadge urgency={item.urgency} />
          <SignalTaxonomyBadges
            domainKey={item.domain_key}
            subjectKey={item.subject_key}
            moduleKey={item.module_key}
            compact
          />
        </div>
        <span className="shrink-0 text-[10px] text-[#aaa]">
          {formatSignalRelativeTime(item.last_activity_at)}
        </span>
      </div>
      <h3 className="text-[13px] font-semibold text-[#1a1a1a]">{item.title}</h3>
      {item.location_text ? (
        <p className="mt-1 text-[11px] text-[#888]">📍 {item.location_text}</p>
      ) : null}
      <div className="mt-2 flex items-center justify-between border-t border-[#F0EFE9] pt-2">
        <span className="text-[11px] text-[#888]">
          {item.is_pinned ? (
            <span className="font-medium text-[#1B4FD8]">Épinglé</span>
          ) : (
            '\u00a0'
          )}
        </span>
        <SignalStatusBadge status={item.status} />
      </div>
    </article>
  )

  if (shouldReduceMotion) {
    return card
  }

  return (
    <motion.div {...terrainTapProps(shouldReduceMotion)}>{card}</motion.div>
  )
}
