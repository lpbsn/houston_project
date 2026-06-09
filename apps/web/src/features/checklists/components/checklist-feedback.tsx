import { TerrainCard } from '@/components/layout/terrain-card'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistFeedbackProps = {
  variant: 'error' | 'success'
  message: string
}

export function ChecklistFeedback({ variant, message }: ChecklistFeedbackProps) {
  return (
    <TerrainCard
      className={cn(
        'text-sm',
        variant === 'error' ? terrain.errorSurface : terrain.successSurface,
      )}
    >
      <p>{message}</p>
    </TerrainCard>
  )
}
