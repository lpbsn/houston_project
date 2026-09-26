import type { ReactNode } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

import {
  terrainSectionDotVariants,
  terrainSectionLabelClassName,
  type TerrainSectionDotVariant,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainCollapsibleFeedSectionProps = {
  label: string
  /** Omit when the real total is unknown (e.g. section still has more pages). */
  count?: number
  /** Shown under the header when the section is collapsed. */
  collapsedHint?: string | null
  dotVariant?: TerrainSectionDotVariant
  expanded: boolean
  onToggle: () => void
  children: ReactNode
  className?: string
}

export function TerrainCollapsibleFeedSection({
  label,
  count,
  collapsedHint,
  dotVariant,
  expanded,
  onToggle,
  children,
  className,
}: TerrainCollapsibleFeedSectionProps) {
  const toggleLabel = expanded
    ? `Replier la section ${label}`
    : `Déplier la section ${label}`
  const title =
    typeof count === 'number' ? `${label} · ${count}` : label

  return (
    <section className={className}>
      <button
        type="button"
        className={cn(terrainSectionLabelClassName('w-full px-3 py-1.5'))}
        onClick={onToggle}
        aria-expanded={expanded}
        aria-label={toggleLabel}
      >
        {dotVariant ? (
          <span
            className={cn(
              'h-1.5 w-1.5 shrink-0 rounded-full',
              terrainSectionDotVariants[dotVariant],
            )}
            aria-hidden
          />
        ) : null}
        <span className="truncate">{title}</span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        )}
      </button>
      {!expanded && collapsedHint ? (
        <p className="px-3 pb-1.5 text-xs text-[#7D7B75]">{collapsedHint}</p>
      ) : null}
      {expanded ? children : null}
    </section>
  )
}
