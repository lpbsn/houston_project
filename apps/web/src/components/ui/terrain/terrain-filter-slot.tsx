import { terrain, terrainFilterSlotClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainFilterSlotProps = {
  label: string
  value: string
  disabled?: boolean
  className?: string
  onClick?: () => void
}

export function TerrainFilterSlot({
  label,
  value,
  disabled = true,
  className,
  onClick,
}: TerrainFilterSlotProps) {
  const content = (
    <>
      <span className={cn('text-[9px] font-semibold uppercase tracking-[0.04em]', terrain.mutedLight)}>
        {label}
      </span>
      <span className={cn('text-[11px] font-bold', terrain.foreground)}>{value}</span>
    </>
  )

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={cn(
          terrainFilterSlotClassName(className),
          'flex w-full flex-1 cursor-pointer text-left',
          disabled && 'cursor-not-allowed opacity-70',
        )}
      >
        {content}
      </button>
    )
  }

  return (
    <div
      className={cn(terrainFilterSlotClassName(className), disabled && 'opacity-70')}
      aria-disabled={disabled || undefined}
    >
      {content}
    </div>
  )
}
