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
      className={cn(className)}
      {...(fieldKey ? { 'data-action-plan-field': fieldKey } : {})}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-[#1a1a1a]">{label}</span>
        {disabled ? (
          <span className="max-w-[55%] truncate text-sm text-[#7D7B75]">{resolvedDisplayValue}</span>
        ) : (
          <PlanningPill
            active={pickerActive}
            aria-label={label}
            onClick={togglePicker}
          >
            <span className="block max-w-[140px] truncate">{resolvedDisplayValue}</span>
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
      {error ? <p className="mt-1 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}
