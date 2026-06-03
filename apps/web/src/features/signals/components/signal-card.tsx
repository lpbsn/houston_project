import { motion } from 'framer-motion'

import { Card } from '@/components/ui/card'

import { SignalStatusBadge } from './signal-status-badge'
import { SignalTaxonomyBadges } from './signal-taxonomy-badges'
import { SignalUrgencyBadge } from './signal-urgency-badge'
import type { SignalFeedItem } from '../types'

type SignalCardProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 60) {
    return `${Math.max(minutes, 1)} min`
  }
  const hours = Math.floor(minutes / 60)
  return `${hours} h`
}

export function SignalCard({ item, onSelect }: SignalCardProps) {
  return (
    <motion.div layout whileTap={{ scale: 0.98 }}>
      <Card
        className={`cursor-pointer gap-3 rounded-2xl border p-4 shadow-sm transition hover:border-[#1b4fd8]/30 ${
          item.is_pinned ? 'border-[#1b4fd8] bg-[#f8faff]' : 'border-[#e7dfd1] bg-white'
        }`}
        onClick={() => onSelect(item.id)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            onSelect(item.id)
          }
        }}
        role="button"
        tabIndex={0}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-wrap gap-1.5">
            <SignalUrgencyBadge urgency={item.urgency} />
            <SignalTaxonomyBadges domainKey={item.domain_key} subjectKey={item.subject_key} />
          </div>
          <span className="shrink-0 text-xs text-[#9a8f82]">{formatRelativeTime(item.last_activity_at)}</span>
        </div>
        <h3 className="text-base font-semibold text-[#2a2218]">{item.title}</h3>
        <p className="line-clamp-2 text-sm text-[#6b5f52]">{item.structured_summary_short}</p>
        {item.location_text ? (
          <p className="text-xs text-[#9a8f82]">📍 {item.location_text}</p>
        ) : null}
        <div className="flex items-center justify-between pt-1">
          <SignalStatusBadge status={item.status} />
          {item.is_pinned ? <span className="text-xs font-medium text-[#1b4fd8]">Épinglé</span> : null}
        </div>
      </Card>
    </motion.div>
  )
}
