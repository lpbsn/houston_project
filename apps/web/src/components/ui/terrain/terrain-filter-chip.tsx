import type { ReactNode } from 'react'

import { terrainFilterChipClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainFilterChipProps = {
  pressed: boolean
  onClick: () => void
  children: ReactNode
  className?: string
}

export function TerrainFilterChip({
  pressed,
  onClick,
  children,
  className,
}: TerrainFilterChipProps) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      className={cn(terrainFilterChipClassName(pressed), className)}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
