import type { PropsWithChildren, ReactNode } from 'react'

import { cn } from '@/lib/utils'

import { TerrainCard } from './terrain-card'
import { TerrainFieldLabel } from './terrain-field-label'

type TerrainDetailFieldCardProps = PropsWithChildren<{
  label: ReactNode
  className?: string
  contentClassName?: string
}>

export function TerrainDetailFieldCard({
  label,
  children,
  className,
  contentClassName,
}: TerrainDetailFieldCardProps) {
  return (
    <TerrainCard className={className}>
      <TerrainFieldLabel>{label}</TerrainFieldLabel>
      <div className={cn('mt-2', contentClassName)}>{children}</div>
    </TerrainCard>
  )
}
