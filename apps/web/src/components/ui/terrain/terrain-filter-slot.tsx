import { terrain, terrainFilterSlotClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainFilterSlotProps = {
  label: string
  value: string
  disabled?: boolean
  className?: string
}

export function TerrainFilterSlot({
  label,
  value,
  disabled = true,
  className,
}: TerrainFilterSlotProps) {
  return (
    <div
      className={cn(terrainFilterSlotClassName(className), disabled && 'opacity-70')}
      aria-disabled={disabled || undefined}
    >
      <span className={cn('text-[9px] font-semibold uppercase tracking-[0.04em]', terrain.mutedLight)}>
        {label}
      </span>
      <span className={cn('text-[11px] font-bold', terrain.foreground)}>{value}</span>
    </div>
  )
}
