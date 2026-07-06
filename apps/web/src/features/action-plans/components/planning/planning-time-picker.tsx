import { snapTimeToFiveMinutes } from '../../lib/action-plan-event-planning-form'
import { toWheelColumnOptions, WheelColumn } from './planning-wheel-column'

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const MINUTE_OPTIONS = Array.from({ length: 12 }, (_, index) => String(index * 5).padStart(2, '0'))

type PlanningTimePickerProps = {
  value: string
  onChange: (time: string) => void
}

function parseTime(value: string): { hour: string; minute: string } {
  const snapped = snapTimeToFiveMinutes(value)
  const match = /^(\d{2}):(\d{2})$/.exec(snapped)
  if (!match) {
    return { hour: '00', minute: '00' }
  }
  return { hour: match[1], minute: match[2] }
}

export function PlanningTimePicker({ value, onChange }: PlanningTimePickerProps) {
  const { hour, minute } = parseTime(value)

  function updateHour(nextHour: string) {
    onChange(snapTimeToFiveMinutes(`${nextHour}:${minute}`))
  }

  function updateMinute(nextMinute: string) {
    onChange(snapTimeToFiveMinutes(`${hour}:${nextMinute}`))
  }

  return (
    <div className="relative px-3 pb-3">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-3 top-1/2 h-9 -translate-y-1/2 rounded-lg bg-[#EEF3FF]"
      />
      <div className="relative flex items-center gap-2">
        <WheelColumn
          label="Heure"
          options={toWheelColumnOptions(HOUR_OPTIONS)}
          value={hour}
          onChange={updateHour}
        />
        <span className="text-sm text-[#7D7B75]" aria-hidden>
          :
        </span>
        <WheelColumn
          label="Minute"
          options={toWheelColumnOptions(MINUTE_OPTIONS)}
          value={minute}
          onChange={updateMinute}
        />
      </div>
    </div>
  )
}
