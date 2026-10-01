import { ChevronRight } from 'lucide-react'

import { cn } from '@/lib/utils'

import { PlanningOptionPicker } from './planning-option-picker'
import { PlanningPill } from './planning-pill'

export type PlanningOptionPickerTarget = {
  rowId: string
} | null

type PlanningOptionRowProps = {
  rowId: string
  label: string
  value: string
  displayValue?: string
  options: Array<{ value: string; label: string }>
  disabled?: boolean
  openPicker: PlanningOptionPickerTarget
  onOpenPickerChange: (target: PlanningOptionPickerTarget) => void
  onChange: (value: string) => void
  error?: string
  fieldKey?: string
  className?: string
  inset?: boolean
  wrapValue?: boolean
  summary?: boolean
}

export function PlanningOptionRow({
  rowId,
  label,
  value,
  displayValue,
  options,
  disabled = false,
  openPicker,
  onOpenPickerChange,
  onChange,
  error,
  fieldKey,
  className,
  inset = false,
  wrapValue = false,
  summary = false,
}: PlanningOptionRowProps) {
  const pickerActive = !disabled && openPicker?.rowId === rowId
  const resolvedDisplayValue =
    displayValue ?? options.find((option) => option.value === value)?.label ?? '—'

  function togglePicker() {
    if (disabled) {
      return
    }
    if (pickerActive) {
      onOpenPickerChange(null)
      return
    }
    onOpenPickerChange({ rowId })
  }

  return (
    <div
      className={cn(
        inset && 'border-b border-[#E8E6DF] px-3 py-3 last:border-b-0',
        summary && 'border-b border-[#E8E6DF] last:border-b-0',
        className,
      )}
      {...(fieldKey ? { 'data-action-plan-field': fieldKey } : {})}
    >
      <div
        className={cn(
          'flex justify-between gap-3',
          wrapValue ? 'items-start' : 'items-center',
          summary && 'px-3 py-3',
        )}
      >
        <span className="shrink-0 text-sm text-[#1a1a1a]">{label}</span>
        {disabled ? (
          <span
            className={cn(
              'text-sm text-[#7D7B75]',
              wrapValue ? 'min-w-0 flex-1 break-words text-right' : 'max-w-[55%] truncate',
            )}
          >
            {resolvedDisplayValue}
          </span>
        ) : summary ? (
          <button
            type="button"
            aria-label={label}
            aria-pressed={pickerActive}
            className="flex min-w-0 items-center gap-1.5 text-sm text-[#7D7B75]"
            onClick={togglePicker}
          >
            <span className="truncate">{resolvedDisplayValue}</span>
            <ChevronRight
              className={cn('size-4 shrink-0 transition-transform', pickerActive && 'rotate-90')}
              aria-hidden
            />
          </button>
        ) : (
          <PlanningPill
            active={pickerActive}
            aria-label={label}
            className={wrapValue ? 'min-w-0 max-w-[70%] shrink' : undefined}
            onClick={togglePicker}
          >
            <span
              className={
                wrapValue ? 'block whitespace-normal break-words text-right' : 'block max-w-[140px] truncate'
              }
            >
              {resolvedDisplayValue}
            </span>
          </PlanningPill>
        )}
      </div>

      {pickerActive ? (
        <PlanningOptionPicker
          ariaLabel={label}
          value={value}
          options={options}
          onChange={onChange}
        />
      ) : null}
      {error ? (
        <p className={cn('mt-1 text-xs text-destructive', summary && 'px-3 pb-2')}>{error}</p>
      ) : null}
    </div>
  )
}
