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
}

export function TerrainSegmentedControl<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  className,
}: TerrainSegmentedControlProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'grid max-w-full overflow-hidden rounded-xl border border-[#E8E6DF] bg-[#F5F4F0] p-0.5',
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
              'min-h-8 min-w-0 whitespace-nowrap rounded-[10px] px-2 py-1.5 text-xs font-semibold sm:px-2.5',
              selected ? 'z-10 bg-white text-[#114660] shadow-sm' : 'z-0 text-[#7D7B75]',
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
