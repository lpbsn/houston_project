import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

import {
  formatDatePillLabel,
  formatTimePillLabel,
  getDefaultPlanningTime,
} from '../../lib/action-plan-event-planning-form'
import { PlanningDatePicker } from './planning-date-picker'
import { PlanningPill } from './planning-pill'
import { PlanningTimePicker } from './planning-time-picker'

export type PlanningPickerTarget = {
  rowId: string
  part: 'date' | 'time'
} | null

type PlanningDateTimeRowProps = {
  rowId: string
  label: string
  date: string
  time: string
  hideTime?: boolean
  hideDate?: boolean
  disabled?: boolean
  openPicker: PlanningPickerTarget
  onOpenPickerChange: (target: PlanningPickerTarget) => void
  onDateChange: (date: string) => void
  onTimeChange: (time: string) => void
  error?: string
  className?: string
  pickerFooter?: ReactNode
  labelAddon?: ReactNode
}

export function PlanningDateTimeRow({
  rowId,
  label,
  date,
  time,
  hideTime = false,
  hideDate = false,
  disabled = false,
  openPicker,
  onOpenPickerChange,
  onDateChange,
  onTimeChange,
  error,
  className,
  pickerFooter,
  labelAddon,
}: PlanningDateTimeRowProps) {
  const dateActive = !disabled && openPicker?.rowId === rowId && openPicker.part === 'date'
  const timeActive = !disabled && openPicker?.rowId === rowId && openPicker.part === 'time'

  function togglePicker(part: 'date' | 'time') {
    if (disabled) {
      return
    }
    if (openPicker?.rowId === rowId && openPicker.part === part) {
      onOpenPickerChange(null)
      return
    }
    if (part === 'time' && !time.trim()) {
      onTimeChange(getDefaultPlanningTime())
    }
    onOpenPickerChange({ rowId, part })
  }

  return (
    <div className={cn('border-b border-[#E8E6DF] last:border-b-0', className)}>
      <div className="flex items-center justify-between gap-3 px-3 py-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-sm text-[#1a1a1a]">{label}</span>
          {disabled ? null : labelAddon}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {!hideDate ? (
            <PlanningPill
              active={dateActive}
              disabled={disabled}
              aria-label={`${label} — date`}
              onClick={() => togglePicker('date')}
            >
              {formatDatePillLabel(date)}
            </PlanningPill>
          ) : null}
          {!hideTime ? (
            <PlanningPill
              active={timeActive}
              disabled={disabled}
              aria-label={`${label} — heure`}
              onClick={() => togglePicker('time')}
            >
              {formatTimePillLabel(time)}
            </PlanningPill>
          ) : null}
        </div>
      </div>

      {dateActive && !hideDate ? (
        <PlanningDatePicker
          value={date}
          onChange={(nextDate) => {
            onDateChange(nextDate)
          }}
        />
      ) : null}
      {!hideTime && timeActive ? (
        <PlanningTimePicker
          value={time}
          onChange={(nextTime) => {
            onTimeChange(nextTime)
          }}
        />
      ) : null}
      {pickerFooter}
      {error ? <p className="px-3 pb-2 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}
