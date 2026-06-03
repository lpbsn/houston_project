import type { ReactNode } from 'react'

import {
  terrainSectionDotVariants,
  terrainSectionLabelClassName,
  type TerrainSectionDotVariant,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainSectionLabelProps = {
  children: ReactNode
  dotVariant?: TerrainSectionDotVariant
  className?: string
}

export function TerrainSectionLabel({ children, dotVariant, className }: TerrainSectionLabelProps) {
  return (
    <div className={terrainSectionLabelClassName(className)}>
      {dotVariant ? (
        <span
          className={cn('h-1.5 w-1.5 shrink-0 rounded-full', terrainSectionDotVariants[dotVariant])}
          aria-hidden
        />
      ) : null}
      {children}
    </div>
  )
}
