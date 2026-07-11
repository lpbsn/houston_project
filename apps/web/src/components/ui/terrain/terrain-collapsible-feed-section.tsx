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
  count: number
  dotVariant?: TerrainSectionDotVariant
  expanded: boolean
  onToggle: () => void
  children: ReactNode
  className?: string
}

export function TerrainCollapsibleFeedSection({
  label,
  count,
  dotVariant,
  expanded,
  onToggle,
  children,
  className,
}: TerrainCollapsibleFeedSectionProps) {
  const toggleLabel = expanded
    ? `Replier la section ${label}`
    : `Déplier la section ${label}`

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
        <span className="truncate">
          {label} · {count}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        )}
      </button>
      {expanded ? children : null}
    </section>
  )
}
