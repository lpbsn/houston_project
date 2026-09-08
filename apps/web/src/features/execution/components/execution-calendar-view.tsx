import { useMemo, useState } from 'react'

import { TerrainBottomSheet, TerrainCollapsibleFeedSection, TerrainErrorState } from '@/components/ui/terrain'
import { formatCivilDateFr, todayCivilDate } from '@/lib/business-timezone'
import { cn } from '@/lib/utils'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import type {
  ActionPlanExecutionCalendarResponse,
  ActionPlanExecutionFeedItem,
} from '@/features/action-plans/types'
import { resolveApiErrorMessage } from '@/lib/error-message'

import {
  calendarEventPresentation,
  resolveCalendarEventChromeDensity,
} from '../lib/execution-calendar-event-display'
import {
  allDayDatesForItem,
  isExecutionAllDay,
  splitOverlappingColumns,
  timedIntervalOnDay,
} from '../lib/execution-calendar-layout'
import type { ExecutionCalendarGranularity } from '../lib/execution-feed-url-state'

const HOUR_HEIGHT = 48
const WEEKDAY_LABELS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
const MONTH_VISIBLE = 3

type ExecutionCalendarViewProps = {
  granularity: ExecutionCalendarGranularity
  days: string[]
  month: string
  data?: ActionPlanExecutionCalendarResponse
  isLoading: boolean
  isError: boolean
  error: unknown
  onRetry: () => void
  onOpenExecution: (executionId: string) => void
}

function hours(): number[] {
  return Array.from({ length: 24 }, (_, hour) => hour)
}

function formatHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

function weekdayIndexMonday(date: string): number {
  const [year, month, day] = date.split('-').map((part) => Number.parseInt(part, 10))
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
  return weekday === 0 ? 6 : weekday - 1
}

function CalendarEventButton({
  item,
  variant,
  heightPx,
  narrow,
  className,
  onSelect,
}: {
  item: ActionPlanExecutionFeedItem
  variant: 'timed' | 'allDay' | 'month'
  heightPx?: number
  narrow?: boolean
  className?: string
  onSelect: () => void
}) {
  const density = resolveCalendarEventChromeDensity({ variant, heightPx, narrow })
  const presentation = calendarEventPresentation(item, density)
  return (
    <button
      type="button"
      className={cn(
        'flex min-h-7 min-w-[2.75rem] items-stretch justify-start overflow-hidden rounded-md border border-black/5 text-left leading-tight',
        className,
      )}
      style={{ backgroundColor: presentation.chrome.background, color: presentation.chrome.text }}
      onClick={onSelect}
    >
      <span
        className="w-[3px] shrink-0"
        style={{ backgroundColor: presentation.chrome.bar }}
        aria-hidden
      />
      <span className="flex min-h-0 min-w-0 flex-1 flex-col items-start justify-start gap-0.5 overflow-hidden px-1.5 py-0.5">
        <span className={cn('w-full font-semibold', variant === 'month' ? 'line-clamp-1 text-[10px]' : 'line-clamp-2 text-[11px]')}>
          {presentation.title}
        </span>
        {presentation.statusLabel ? (
          <span className="flex min-w-0 items-center gap-1 text-[10px] font-medium opacity-80">
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: presentation.chrome.bar }}
              aria-hidden
            />
            <span className="truncate">{presentation.statusLabel}</span>
          </span>
        ) : null}
        {presentation.assigneeInitials.length > 0 ? (
          <span className="truncate text-[10px] font-medium opacity-80">
            {presentation.assigneeInitials.join(' · ')}
          </span>
        ) : null}
        {presentation.orgBadges.length > 0 ? (
          <span className="flex min-w-0 flex-wrap gap-0.5">
            {presentation.orgBadges.map((badge) => (
              <span
                key={badge}
                className="max-w-full truncate rounded bg-white/70 px-1 py-px text-[9px] font-semibold"
              >
                {badge}
              </span>
            ))}
          </span>
        ) : null}
      </span>
    </button>
  )
}

function AllDayLane({
  days,
  items,
  onOpenExecution,
}: {
  days: string[]
  items: ActionPlanExecutionFeedItem[]
  onOpenExecution: (executionId: string) => void
}) {
  return (
    <div className="grid shrink-0 border-b border-[#E8E6DF] bg-white" style={{ gridTemplateColumns: `3rem repeat(${days.length}, minmax(0, 1fr))` }}>
      <div className="px-1 py-2 text-[10px] font-semibold uppercase tracking-wide text-[#7D7B75]">
        Journée
      </div>
      {days.map((day) => {
        const dayItems = items.filter((item) => allDayDatesForItem(item).includes(day))
        return (
          <div key={day} className="flex min-h-10 flex-col gap-1 border-l border-[#E8E6DF] px-1 py-1">
            {dayItems.map((item) => (
              <CalendarEventButton
                key={item.id}
                item={item}
                variant="allDay"
                onSelect={() => onOpenExecution(item.id)}
              />
            ))}
          </div>
        )
      })}
    </div>
  )
}

function TimedDayColumn({
  day,
  items,
  narrow,
  onOpenExecution,
}: {
  day: string
  items: ActionPlanExecutionFeedItem[]
  narrow?: boolean
  onOpenExecution: (executionId: string) => void
}) {
  const blocks = splitOverlappingColumns(
    items.flatMap((item) => {
      const interval = timedIntervalOnDay(item, day)
      return interval ? [{ item, ...interval }] : []
    }),
  )

  return (
    <div className="relative border-l border-[#E8E6DF]" style={{ height: hours().length * HOUR_HEIGHT }}>
      {hours().map((hour) => (
        <div
          key={hour}
          className="absolute inset-x-0 border-t border-[#F0EFE9]"
          style={{ top: hour * HOUR_HEIGHT }}
        />
      ))}
      {blocks.map((block) => {
        const widthPct = 100 / block.columnCount
        const heightPx = Math.max(24, ((block.endMin - block.startMin) / 60) * HOUR_HEIGHT)
        return (
          <div
            key={block.item.id}
            className="absolute px-1"
            style={{
              top: (block.startMin / 60) * HOUR_HEIGHT,
              height: heightPx,
              left: `${block.column * widthPct}%`,
              width: `${widthPct}%`,
            }}
          >
            <CalendarEventButton
              item={block.item}
              variant="timed"
              heightPx={heightPx}
              narrow={narrow}
              className="h-full w-full"
              onSelect={() => onOpenExecution(block.item.id)}
            />
          </div>
        )
      })}
    </div>
  )
}

function TimeGrid({
  days,
  items,
  onOpenExecution,
}: {
  days: string[]
  items: ActionPlanExecutionFeedItem[]
  onOpenExecution: (executionId: string) => void
}) {
  const timedItems = items.filter((item) => !isExecutionAllDay(item) && item.start_at)
  const narrow = days.length > 1
  return (
    <div className="grid" style={{ gridTemplateColumns: `3rem repeat(${days.length}, minmax(0, 1fr))` }}>
      <div className="relative pt-1" style={{ height: hours().length * HOUR_HEIGHT }}>
        {hours().map((hour) => (
          <div
            key={hour}
            className="absolute inset-x-0 pr-1 pt-0.5 text-right text-[10px] text-[#7D7B75]"
            style={{ top: hour * HOUR_HEIGHT }}
          >
            {formatHour(hour)}
          </div>
        ))}
      </div>
      {days.map((day) => (
        <TimedDayColumn
          key={day}
          day={day}
          items={timedItems}
          narrow={narrow}
          onOpenExecution={onOpenExecution}
        />
      ))}
    </div>
  )
}

function MonthOverflowSheet({
  day,
  items,
  open,
  onClose,
  onOpenExecution,
}: {
  day: string
  items: ActionPlanExecutionFeedItem[]
  open: boolean
  onClose: () => void
  onOpenExecution: (executionId: string) => void
}) {
  return (
    <TerrainBottomSheet title={formatCivilDateFr(day)} open={open} onClose={onClose}>
      <div className="flex flex-col gap-2 p-3">
        {items.map((item) => (
          <CalendarEventButton
            key={item.id}
            item={item}
            variant={isExecutionAllDay(item) ? 'allDay' : 'timed'}
            className="min-h-10 w-full"
            onSelect={() => {
              onClose()
              onOpenExecution(item.id)
            }}
          />
        ))}
      </div>
    </TerrainBottomSheet>
  )
}

export function ExecutionCalendarView({
  granularity,
  days,
  month,
  data,
  isLoading,
  isError,
  error,
  onRetry,
  onOpenExecution,
}: ExecutionCalendarViewProps) {
  const today = todayCivilDate()
  const [overflowDay, setOverflowDay] = useState<string | null>(null)
  const items = data ? unwrapActionPlanExecutionFeedItems(data.items) : []
  const unplanned = data ? unwrapActionPlanExecutionFeedItems(data.unplanned) : []
  const allDayItems = items.filter(isExecutionAllDay)
  const overflowItems = useMemo(
    () => (overflowDay ? items.filter((item) => {
      if (isExecutionAllDay(item)) {
        return allDayDatesForItem(item).includes(overflowDay)
      }
      return timedIntervalOnDay(item, overflowDay) != null
    }) : []),
    [items, overflowDay],
  )

  if (isLoading) {
    return <p className="px-1 py-8 text-center text-sm text-[#7D7B75]">Chargement du calendrier…</p>
  }

  if (isError) {
    return (
      <TerrainErrorState
        message={resolveApiErrorMessage(
          error,
          ActionPlansApiError,
          'Impossible de charger le calendrier.',
        )}
        onRetry={onRetry}
      />
    )
  }

  const header = (
    <div
      className="grid shrink-0 border-b border-[#E8E6DF] bg-white"
      style={{ gridTemplateColumns: granularity === 'day' ? '3rem 1fr' : `3rem repeat(${days.length}, minmax(4.5rem, 1fr))` }}
    >
      <div />
      {days.map((day) => (
        <div
          key={day}
          className={cn(
            'border-l border-[#E8E6DF] px-1 py-2 text-center text-xs font-semibold text-[#1a1a1a]',
            day === today && 'text-[#114660]',
          )}
        >
          <div className="uppercase text-[10px] text-[#7D7B75]">{WEEKDAY_LABELS[weekdayIndexMonday(day)]}</div>
          <div className={cn('mx-auto mt-0.5 flex h-7 w-7 items-center justify-center rounded-full', day === today && 'bg-[#114660] text-white')}>
            {Number.parseInt(day.slice(8, 10), 10)}
          </div>
        </div>
      ))}
    </div>
  )

  if (granularity === 'month') {
    const weeks: string[][] = []
    for (let index = 0; index < days.length; index += 7) {
      weeks.push(days.slice(index, index + 7))
    }
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
        <UnplannedBanner items={unplanned} onOpenExecution={onOpenExecution} />
        <div className="overflow-hidden rounded-xl border border-[#E8E6DF] bg-white">
          <div className="grid grid-cols-7 border-b border-[#E8E6DF]">
            {WEEKDAY_LABELS.map((label) => (
              <div key={label} className="px-1 py-2 text-center text-[10px] font-semibold uppercase text-[#7D7B75]">
                {label}
              </div>
            ))}
          </div>
          {weeks.map((week) => (
            <div key={week[0]} className="grid grid-cols-7 border-b border-[#E8E6DF] last:border-b-0">
              {week.map((day) => {
                const dayItems = items.filter((item) => {
                  if (isExecutionAllDay(item)) {
                    return allDayDatesForItem(item).includes(day)
                  }
                  return timedIntervalOnDay(item, day) != null
                })
                const visible = dayItems.slice(0, MONTH_VISIBLE)
                const extra = dayItems.length - visible.length
                const inMonth = day.startsWith(month)
                return (
                  <div
                    key={day}
                    className={cn(
                      'min-h-24 border-l border-[#E8E6DF] px-1 py-1 first:border-l-0',
                      !inMonth && 'bg-[#FAFAF7] text-[#B0ADA6]',
                      day === today && 'bg-[#F3F7F9]',
                    )}
                  >
                    <div className={cn('mb-1 text-right text-xs font-semibold', day === today && 'text-[#114660]')}>
                      {Number.parseInt(day.slice(8, 10), 10)}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {visible.map((item) => (
                        <CalendarEventButton
                          key={item.id}
                          item={item}
                          variant="month"
                          className="min-h-7 w-full"
                          onSelect={() => onOpenExecution(item.id)}
                        />
                      ))}
                      {extra > 0 ? (
                        <button
                          type="button"
                          className="text-left text-[10px] font-semibold text-[#114660]"
                          onClick={() => setOverflowDay(day)}
                        >
                          +{extra} de plus
                        </button>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
        <MonthOverflowSheet
          day={overflowDay ?? ''}
          items={overflowItems}
          open={overflowDay != null}
          onClose={() => setOverflowDay(null)}
          onOpenExecution={onOpenExecution}
        />
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <UnplannedBanner items={unplanned} onOpenExecution={onOpenExecution} />
      <div
        className={cn(
          'flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[#E8E6DF] bg-white',
          granularity === 'week' && 'overflow-x-auto overscroll-x-contain',
        )}
      >
        <div
          className={cn(
            'flex min-h-0 min-w-0 flex-1 flex-col',
            granularity === 'week' && 'min-w-[44rem]',
          )}
        >
          {header}
          <AllDayLane days={days} items={allDayItems} onOpenExecution={onOpenExecution} />
          <div
            data-testid="calendar-time-scroller"
            className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain"
          >
            <TimeGrid days={days} items={items} onOpenExecution={onOpenExecution} />
          </div>
        </div>
      </div>
    </div>
  )
}

function UnplannedBanner({
  items,
  onOpenExecution,
}: {
  items: ActionPlanExecutionFeedItem[]
  onOpenExecution: (executionId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  if (items.length === 0) {
    return null
  }
  return (
    <TerrainCollapsibleFeedSection
      label="Non planifiés"
      count={items.length}
      expanded={expanded}
      onToggle={() => setExpanded((current) => !current)}
    >
      <div className="flex flex-col gap-1">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="rounded-lg border border-[#E8E6DF] bg-white px-3 py-2 text-left text-sm font-medium text-[#1a1a1a]"
            onClick={() => onOpenExecution(item.id)}
          >
            {item.title}
          </button>
        ))}
      </div>
    </TerrainCollapsibleFeedSection>
  )
}
