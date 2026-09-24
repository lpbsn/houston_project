import type { ReactNode } from 'react'

import { HoustonBadge } from '@/components/ui/terrain'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'
import { cn } from '@/lib/utils'

type SignalClassificationBadgesProps = {
  signal: SignalClassificationInput
  className?: string
  /** Badges rendered on the same row as the primary chip (above `Concerné`). */
  leading?: ReactNode
  /** Omits the stacked affected line when the caller places that pole elsewhere. */
  hideAffectedLine?: boolean
  /** Desktop feed shows the full pole and subject, wrapping instead of truncating. */
  wrapLabel?: boolean
}

export function SignalClassificationBadges({
  signal,
  className,
  leading,
  hideAffectedLine = false,
  wrapLabel = false,
}: SignalClassificationBadgesProps) {
  const classification = formatSignalClassification(signal)
  const hasPrimary = Boolean(classification.primaryLine)
  const hasAffected = !hideAffectedLine && Boolean(classification.affectedLine)
  const hasLeading = Boolean(leading)

  if (!hasPrimary && !hasAffected && !hasLeading) {
    return null
  }

  return (
    <span className={cn('inline-flex min-w-0 max-w-full flex-col gap-0.5', className)}>
      {hasLeading || hasPrimary ? (
        <span className="inline-flex min-w-0 flex-wrap items-center gap-1">
          {leading}
          {hasPrimary ? (
            <HoustonBadge
              variant="gray"
              className={
                wrapLabel
                  ? 'block min-w-0 max-w-full whitespace-normal break-words text-left leading-snug'
                  : undefined
              }
            >
              {classification.primaryLine}
            </HoustonBadge>
          ) : null}
        </span>
      ) : null}
      {hasAffected ? (
        <span className="text-[11px] text-[#888]">{classification.affectedLine}</span>
      ) : null}
    </span>
  )
}
