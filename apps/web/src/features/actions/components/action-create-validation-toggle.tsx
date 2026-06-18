import { useId } from 'react'

import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type ActionCreateValidationToggleProps = {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label?: string
}

export function ActionCreateValidationToggle({
  checked,
  onCheckedChange,
  label = 'Validation requise',
}: ActionCreateValidationToggleProps) {
  const labelId = useId()

  return (
    <TerrainCard>
      <div className="flex min-h-11 items-center justify-between gap-3">
        <span id={labelId} className="text-sm text-[#1a1a1a]">
          {label}
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-labelledby={labelId}
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
    </TerrainCard>
  )
}
