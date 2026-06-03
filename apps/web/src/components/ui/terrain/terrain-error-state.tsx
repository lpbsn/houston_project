import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { terrainErrorStateClassName } from '@/lib/terrain-styles'

type TerrainErrorStateProps = {
  message: ReactNode
  onRetry?: () => void
  retryLabel?: string
  className?: string
}

export function TerrainErrorState({
  message,
  onRetry,
  retryLabel = 'Réessayer',
  className,
}: TerrainErrorStateProps) {
  return (
    <div className={terrainErrorStateClassName(className)} role="alert">
      <div>{message}</div>
      {onRetry ? (
        <Button
          type="button"
          variant="outline"
          className="mt-3 rounded-xl border-[#E8E6DF]"
          onClick={onRetry}
        >
          {retryLabel}
        </Button>
      ) : null}
    </div>
  )
}
