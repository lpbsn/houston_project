import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMemo, useState } from 'react'

import { cn } from '@/lib/utils'

const WEEKDAY_LABELS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'] as const

function toDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateKey(value: string): Date | null {
  if (!value.trim()) {
    return null
  }
  const parsed = Date.parse(`${value.trim()}T12:00:00`)
  if (Number.isNaN(parsed)) {
    return null
  }
  return new Date(parsed)
}

function buildCalendarCells(year: number, month: number): (Date | null)[] {
  const firstOfMonth = new Date(year, month, 1)
  const startOffset = (firstOfMonth.getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (Date | null)[] = Array.from({ length: startOffset }, () => null)
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(year, month, day))
  }
  while (cells.length % 7 !== 0) {
    cells.push(null)
  }
  return cells
}

type PlanningDatePickerProps = {
  value: string
  onChange: (date: string) => void
}

export function PlanningDatePicker({ value, onChange }: PlanningDatePickerProps) {
  const selectedDate = parseDateKey(value)
  const todayKey = toDateKey(new Date())
  const initialView = selectedDate ?? new Date()
  const [viewYear, setViewYear] = useState(initialView.getFullYear())
  const [viewMonth, setViewMonth] = useState(initialView.getMonth())

  const monthLabel = new Intl.DateTimeFormat('fr-FR', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(viewYear, viewMonth, 1))

  const cells = useMemo(
    () => buildCalendarCells(viewYear, viewMonth),
    [viewMonth, viewYear],
  )

  function shiftMonth(delta: number) {
    const next = new Date(viewYear, viewMonth + delta, 1)
    setViewYear(next.getFullYear())
    setViewMonth(next.getMonth())
  }

  return (
    <div className="px-3 pb-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-medium capitalize text-[#1a1a1a]">{monthLabel}</p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded-lg p-2 text-[#1B4FD8] active:bg-[#F5F4F0]"
            aria-label="Mois précédent"
            onClick={() => shiftMonth(-1)}
          >
            <ChevronLeft className="size-4" aria-hidden />
          </button>
          <button
            type="button"
            className="rounded-lg p-2 text-[#1B4FD8] active:bg-[#F5F4F0]"
            aria-label="Mois suivant"
            onClick={() => shiftMonth(1)}
          >
            <ChevronRight className="size-4" aria-hidden />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-medium uppercase text-[#7D7B75]">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label} className="py-1">
            {label}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell, index) => {
          if (!cell) {
            return <span key={`empty-${index}`} aria-hidden />
          }
          const cellKey = toDateKey(cell)
          const isSelected = value === cellKey
          const isToday = cellKey === todayKey
          return (
            <button
              key={cellKey}
              type="button"
              className={cn(
                'mx-auto flex h-9 w-9 items-center justify-center rounded-full text-sm',
                isSelected
                  ? 'bg-[#1B4FD8] text-white'
                  : isToday
                    ? 'text-[#1B4FD8]'
                    : 'text-[#1a1a1a] active:bg-[#F5F4F0]',
              )}
              aria-label={new Intl.DateTimeFormat('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              }).format(cell)}
              aria-pressed={isSelected}
              onClick={() => onChange(cellKey)}
            >
              {cell.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}
