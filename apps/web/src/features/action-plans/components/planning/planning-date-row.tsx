import { cn } from '@/lib/utils'

import { formatDatePillLabel } from '../../lib/action-plan-event-planning-form'
import { PlanningDatePicker } from './planning-date-picker'
import { PlanningPill } from './planning-pill'
import type { PlanningPickerTarget } from './planning-date-time-row'

type PlanningDateRowProps = {
  rowId: string
  label: string
  date: string
  openPicker: PlanningPickerTarget
  onOpenPickerChange: (target: PlanningPickerTarget) => void
  onDateChange: (date: string) => void
  error?: string
  className?: string
}

export function PlanningDateRow({
  rowId,
  label,
  date,
  openPicker,
  onOpenPickerChange,
  onDateChange,
  error,
  className,
}: PlanningDateRowProps) {
  const dateActive = openPicker?.rowId === rowId && openPicker.part === 'date'

  function toggleDatePicker() {
    if (dateActive) {
      onOpenPickerChange(null)
      return
    }
    onOpenPickerChange({ rowId, part: 'date' })
  }

  return (
    <div className={cn('border-b border-[#E8E6DF] last:border-b-0', className)}>
      <div className="flex items-center justify-between gap-3 px-3 py-3">
        <span className="text-sm text-[#1a1a1a]">{label}</span>
        <PlanningPill active={dateActive} aria-label={`${label} — date`} onClick={toggleDatePicker}>
          {formatDatePillLabel(date)}
        </PlanningPill>
      </div>
      {dateActive ? <PlanningDatePicker value={date} onChange={onDateChange} /> : null}
      {error ? <p className="px-3 pb-2 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}
