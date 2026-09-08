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
        'inline-flex max-w-full items-center rounded-xl border border-[#E8E6DF] bg-[#F5F4F0] p-0.5',
        className,
      )}
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
              'min-h-8 min-w-0 flex-1 rounded-[10px] px-3 py-1.5 text-xs font-semibold',
              selected ? 'bg-white text-[#114660] shadow-sm' : 'text-[#7D7B75]',
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
