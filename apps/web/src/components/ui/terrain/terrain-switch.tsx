import { useId } from 'react'

import { cn } from '@/lib/utils'

type TerrainSwitchProps = {
  label: string
  checked: boolean
  disabled?: boolean
  onCheckedChange: (checked: boolean) => void
  variant?: 'default' | 'bordered'
}

export function TerrainSwitch({
  label,
  checked,
  disabled = false,
  onCheckedChange,
  variant = 'default',
}: TerrainSwitchProps) {
  const labelId = useId()

  return (
    <div
      className={cn(
        'flex min-h-11 items-center justify-between gap-3',
        variant === 'bordered'
          ? 'border-b border-[#E8E6DF] px-3 py-3 text-sm last:border-b-0'
          : 'px-4 py-3.5',
        disabled && 'opacity-60',
      )}
    >
      <span id={labelId} className="text-sm text-[#1a1a1a]">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        disabled={disabled}
        className={cn(
          'relative h-7 w-12 shrink-0 rounded-full transition-colors',
          checked ? 'bg-[#1D9E75]' : 'bg-[#E8E6DF]',
        )}
        onClick={() => onCheckedChange(!checked)}
      >
        <span
          aria-hidden
          className={cn(
            'absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0',
          )}
        />
      </button>
    </div>
  )
}
