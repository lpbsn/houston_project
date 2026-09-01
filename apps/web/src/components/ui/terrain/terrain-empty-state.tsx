import type { ReactNode } from 'react'

import { terrain, terrainEmptyStateClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainEmptyStateProps = {
  title: string
  description?: ReactNode
  icon?: ReactNode
  className?: string
}

export function TerrainEmptyState({ title, description, icon, className }: TerrainEmptyStateProps) {
  return (
    <div className={terrainEmptyStateClassName(className)}>
      {icon ? (
        <div className={cn('mb-3 flex justify-center', terrain.textSecondary)} aria-hidden>
          {icon}
        </div>
      ) : null}
      <p className={cn('text-sm font-medium', terrain.foreground)}>{title}</p>
      {description ? (
        <p className={cn('mt-1 text-xs', terrain.textSecondary)}>{description}</p>
      ) : null}
    </div>
  )
}
