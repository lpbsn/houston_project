import type { ReactNode } from 'react'

import { terrainFilterPillClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainFilterPillProps = {
  active: boolean
  disabled?: boolean
  onClick: () => void
  children: ReactNode
  className?: string
}

export function TerrainFilterPill({
  active,
  disabled = false,
  onClick,
  children,
  className,
}: TerrainFilterPillProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(terrainFilterPillClassName(active, className), disabled && 'opacity-50')}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
