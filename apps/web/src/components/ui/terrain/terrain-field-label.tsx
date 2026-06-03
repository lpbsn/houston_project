import type { ReactNode } from 'react'

import { terrainFieldLabelClassName } from '@/lib/terrain-styles'

type TerrainFieldLabelProps = {
  children: ReactNode
  htmlFor?: string
  className?: string
}

export function TerrainFieldLabel({ children, htmlFor, className }: TerrainFieldLabelProps) {
  const Tag = htmlFor ? 'label' : 'p'
  return (
    <Tag className={terrainFieldLabelClassName(className)} htmlFor={htmlFor}>
      {children}
    </Tag>
  )
}
