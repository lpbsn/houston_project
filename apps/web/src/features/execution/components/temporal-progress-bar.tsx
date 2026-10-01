import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function TemporalProgressBar({ percent }: { percent: number }) {
  const clamped = Math.min(100, Math.max(0, percent))
  const fillWidth = clamped + '%'
  const knobLeft = 'calc(' + String(clamped) + '% - 5px)'
  return (
    <div
      className="relative mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[#EFEDE7]"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Progression temporelle"
    >
      <div className={cn('h-full rounded-full', terrainBrandAction.bg)} style={{ width: fillWidth }} />
      <span
        className={cn(
          'absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-white',
          terrainBrandAction.bg,
        )}
        style={{ left: knobLeft }}
        aria-hidden
      />
    </div>
  )
}
