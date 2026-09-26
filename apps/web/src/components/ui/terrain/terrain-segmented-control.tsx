import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type TerrainSegmentedOption<T extends string> = {
  value: T
  label: ReactNode
}

type TerrainSegmentedControlProps<T extends string> = {
  value: T
  options: readonly TerrainSegmentedOption<T>[]
  onChange: (value: T) => void
  ariaLabel: string
  className?: string
  /** Compact chrome for dense mobile hub headers. Default keeps existing surfaces. */
  size?: 'default' | 'compact'
}

export function TerrainSegmentedControl<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  className,
  size = 'default',
}: TerrainSegmentedControlProps<T>) {
  const compact = size === 'compact'
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'grid max-w-full overflow-hidden',
        compact
          ? 'rounded-md border border-[#E8E6DF]/70 bg-[#F8F7F4] p-px'
          : 'rounded-xl border border-[#E8E6DF] bg-[#F5F4F0] p-0.5',
        className,
      )}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            className={cn(
              'min-w-0 whitespace-nowrap',
              compact
                ? cn(
                    'min-h-7 rounded-[5px] px-2 py-1 text-[12px] font-medium leading-none',
                    selected
                      ? 'z-10 bg-white text-[#114660] shadow-[0_1px_1px_rgba(26,26,26,0.04)]'
                      : 'z-0 text-[#8A8780]',
                  )
                : cn(
                    'min-h-8 rounded-[10px] px-2 py-1.5 text-xs font-semibold sm:px-2.5',
                    selected ? 'z-10 bg-white text-[#114660] shadow-sm' : 'z-0 text-[#7D7B75]',
                  ),
            )}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
