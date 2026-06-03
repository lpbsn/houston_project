import type { ReactNode } from 'react'

import { TerrainCard } from '@/components/ui/terrain/terrain-card'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainComingSoonStateProps = {
  title: string
  description: ReactNode
}

export function TerrainComingSoonState({ title, description }: TerrainComingSoonStateProps) {
  return (
    <TerrainCard className="mx-3 mt-2" aria-label={`${title} — bientôt disponible`}>
      <h2 className={cn('text-base font-semibold', terrain.foreground)}>{title}</h2>
      <p className={cn('mt-2 text-sm leading-relaxed', terrain.muted)}>{description}</p>
    </TerrainCard>
  )
}
