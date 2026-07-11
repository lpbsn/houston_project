import { cn } from '@/lib/utils'

import {
  ACTION_PLAN_RECURRENCE_DAY_LABELS,
  ACTION_PLAN_RECURRENCE_DAYS,
  type ActionPlanRecurrenceDay,
} from '../../lib/action-plan-schedule-constants'

type RecurrenceDaysPickerProps = {
  value: ActionPlanRecurrenceDay[]
  onChange: (days: ActionPlanRecurrenceDay[]) => void
  error?: string
}

export function RecurrenceDaysPicker({ value, onChange, error }: RecurrenceDaysPickerProps) {
  function toggleDay(day: ActionPlanRecurrenceDay) {
    const nextDays = value.includes(day) ? value.filter((item) => item !== day) : [...value, day]
    onChange(nextDays)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {ACTION_PLAN_RECURRENCE_DAYS.map((day) => {
          const selected = value.includes(day)
          return (
            <button
              key={day}
              type="button"
              className={cn(
                'rounded-full border px-3 py-1 text-xs',
                selected
                  ? 'border-[#1a1a1a] bg-[#1a1a1a] text-white'
                  : 'border-[#E8E6DF] text-[#1a1a1a]',
              )}
              onClick={() => toggleDay(day)}
            >
              {ACTION_PLAN_RECURRENCE_DAY_LABELS[day]}
            </button>
          )
        })}
      </div>
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  )
}
