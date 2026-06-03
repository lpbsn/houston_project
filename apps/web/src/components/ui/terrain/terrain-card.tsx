import type { PropsWithChildren } from 'react'

import { terrainCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainCardProps = PropsWithChildren<{
  className?: string
  padding?: 'sm' | 'md'
}>

export function TerrainCard({ children, className, padding = 'md' }: TerrainCardProps) {
  return (
    <div
      className={terrainCardClassName(
        cn(padding === 'sm' ? 'p-3' : 'p-4', className),
      )}
    >
      {children}
    </div>
  )
}
