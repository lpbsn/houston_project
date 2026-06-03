import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainOrDividerProps = {
  label?: string
}

export function TerrainOrDivider({ label = 'ou décris par écrit' }: TerrainOrDividerProps) {
  return (
    <div className="flex items-center gap-2 px-1">
      <div className="h-px flex-1 bg-[#E8E6DF]" />
      <span className={cn('text-[11px]', terrain.mutedLight)}>{label}</span>
      <div className="h-px flex-1 bg-[#E8E6DF]" />
    </div>
  )
}
