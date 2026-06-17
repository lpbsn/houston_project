import { ChevronRight } from 'lucide-react'

import { cn } from '@/lib/utils'

type ChecklistOptionRowProps = {
  label: string
  value: string
  onClick?: () => void
  disabled?: boolean
  error?: string | null
  ariaLabel?: string
}

export function ChecklistOptionRow({
  label,
  value,
  onClick,
  disabled = false,
  error,
  ariaLabel,
}: ChecklistOptionRowProps) {
  const content = (
    <>
      <span className="text-sm text-[#555]">{label}</span>
      <span className="flex min-w-0 items-center gap-1">
        <span className="truncate text-sm font-medium tabular-nums text-[#1a1a1a]">{value}</span>
        {onClick && !disabled ? (
          <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        ) : null}
      </span>
    </>
  )

  if (!onClick || disabled) {
    return (
      <div className="space-y-1">
        <div
          className={cn(
            'flex min-h-11 items-center justify-between gap-3 px-4 py-3.5',
            disabled ? 'opacity-70' : undefined,
          )}
        >
          {content}
        </div>
        {error ? <p className="px-4 pb-2 text-xs text-destructive">{error}</p> : null}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        className={cn(
          'flex min-h-11 w-full items-center justify-between gap-3 px-4 py-3.5 text-left',
          'transition active:bg-[#F5F4F0]',
        )}
        aria-label={ariaLabel ?? label}
        onClick={onClick}
      >
        {content}
      </button>
      {error ? <p className="px-4 pb-2 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}
