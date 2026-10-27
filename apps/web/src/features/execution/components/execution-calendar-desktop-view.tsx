import { useMemo } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  CALENDAR_DAY_GROUP_LABEL,
  calendarEventDesktopAssignees,
  calendarEventEstablishmentLabel,
  calendarEventPilotLabel,
  calendarEventPresentation,
  calendarEventScheduleLabel,
  formatCalendarExecutionCount,
  formatCalendarOverflowLabel,
} from '../lib/execution-calendar-event-display'
import {
  buildDesktopDayLayout,
  buildDesktopMonthRow,
  buildDesktopWeekLayout,
  type CalendarSpan,
  type DesktopMonthRowLayout,
} from '../lib/execution-calendar-layout'
import type { ExecutionCalendarGranularity } from '../lib/execution-feed-url-state'

const WEEKDAY_LABELS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
const DESKTOP_WEEK_COLUMN_MIN_REM = 11

type DesktopExecutionCalendarProps = {
  granularity: ExecutionCalendarGranularity
  days: string[]
  month: string
  items: ActionPlanExecutionFeedItem[]
  timeZone: string
  today: string
  showEstablishment: boolean
  showEmpty: boolean
  onOpenExecution: (executionId: string) => void
  onOpenDay: (anchor: string) => void
}

function weekdayIndexMonday(date: string): number {
  const [year, month, day] = date.split('-').map((part) => Number.parseInt(part, 10))
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
  return weekday === 0 ? 6 : weekday - 1
}

function eventAccessibleLabel(
  item: ActionPlanExecutionFeedItem,
  timeZone: string,
  showEstablishment: boolean,
): string {
  const presentation = calendarEventPresentation(item)
  const assignees = calendarEventDesktopAssignees(item.assignees)
  return [
    presentation.title,
    presentation.statusLabel,
    calendarEventScheduleLabel(item, timeZone) ?? '',
    calendarEventPilotLabel(item),
    assignees.visible.join(', '),
    assignees.overflow > 0 ? `+${assignees.overflow}` : '',
    showEstablishment ? calendarEventEstablishmentLabel(item) : '',
  ]
    .filter((part) => part.length > 0)
    .join(' · ')
}

function EventLines({
  item,
  timeZone,
  showEstablishment,
  showAssignees,
}: {
  item: ActionPlanExecutionFeedItem
  timeZone: string
  showEstablishment: boolean
  showAssignees: boolean
}) {
  const presentation = calendarEventPresentation(item)
  const schedule = calendarEventScheduleLabel(item, timeZone)
  const pilot = calendarEventPilotLabel(item)
  const establishment = showEstablishment ? calendarEventEstablishmentLabel(item) : ''
  const assignees = calendarEventDesktopAssignees(item.assignees)
  const assigneeLabel =
    assignees.visible.length === 0
      ? ''
      : assignees.overflow > 0
        ? `${assignees.visible.join(', ')} +${assignees.overflow}`
        : assignees.visible.join(', ')
  return (
    <>
      <span className="block truncate text-xs font-semibold">{presentation.title}</span>
      <span className="block truncate text-[11px] font-medium">{presentation.statusLabel}</span>
      {schedule ? <span className="block truncate text-[11px] tabular-nums">{schedule}</span> : null}
      {pilot ? <span className="block truncate text-[11px]">{pilot}</span> : null}
      {showAssignees && assigneeLabel ? (
        <span className="block truncate text-[11px]">{assigneeLabel}</span>
      ) : null}
      {establishment ? (
        <span
          data-testid={`calendar-establishment-${item.id}`}
          className="block truncate text-[11px] font-medium"
        >
          {establishment}
        </span>
      ) : null}
    </>
  )
}

function EventCard({
  item,
  timeZone,
  showEstablishment,
  onOpenExecution,
}: {
  item: ActionPlanExecutionFeedItem
  timeZone: string
  showEstablishment: boolean
  onOpenExecution: (executionId: string) => void
}) {
  const presentation = calendarEventPresentation(item)
  return (
    <button
      type="button"
      data-testid={`calendar-event-${item.id}`}
      className="flex w-full min-w-0 flex-col gap-0.5 rounded-lg border border-black/10 px-2 py-1.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#114660]"
      style={{
        backgroundColor: presentation.chrome.background,
        color: presentation.chrome.text,
        borderLeft: `3px solid ${presentation.chrome.bar}`,
      }}
      aria-label={eventAccessibleLabel(item, timeZone, showEstablishment)}
      onClick={() => onOpenExecution(item.id)}
    >
      <EventLines item={item} timeZone={timeZone} showEstablishment={showEstablishment} showAssignees />
    </button>
  )
}

function BandButton({
  span,
  timeZone,
  showEstablishment,
  onOpenExecution,
}: {
  span: CalendarSpan
  timeZone: string
  showEstablishment: boolean
  onOpenExecution: (executionId: string) => void
}) {
  const presentation = calendarEventPresentation(span.item)
  const continuesBefore = span.continuesBefore ? 'Commencé avant cette période' : ''
  const continuesAfter = span.continuesAfter ? 'Se poursuit après cette période' : ''
  const label = [eventAccessibleLabel(span.item, timeZone, showEstablishment), continuesBefore, continuesAfter]
    .filter((part) => part.length > 0)
    .join(' · ')
  return (
    <button
      type="button"
      data-testid={`calendar-span-${span.item.id}`}
      data-continues-before={span.continuesBefore || undefined}
      data-continues-after={span.continuesAfter || undefined}
      className={cn(
        'relative z-10 mx-1 flex min-h-10 min-w-0 items-center gap-1 overflow-hidden rounded-lg border border-black/10 px-2 py-1 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#114660]',
        span.continuesBefore && 'ml-0 rounded-l-none',
        span.continuesAfter && 'mr-0 rounded-r-none',
      )}
      style={{
        gridColumn: `${span.startColumn + 1} / ${span.endColumn + 2}`,
        gridRow: span.lane + 1,
        backgroundColor: presentation.chrome.background,
        color: presentation.chrome.text,
        borderLeft: span.continuesBefore ? undefined : `3px solid ${presentation.chrome.bar}`,
      }}
      aria-label={label}
      onClick={() => onOpenExecution(span.item.id)}
    >
      {span.continuesBefore ? <ChevronLeft className="h-3 w-3 shrink-0" aria-hidden /> : null}
      <span className="min-w-0 flex-1">
        <EventLines
          item={span.item}
          timeZone={timeZone}
          showEstablishment={showEstablishment}
          showAssignees={false}
        />
      </span>
      {span.continuesAfter ? <ChevronRight className="h-3 w-3 shrink-0" aria-hidden /> : null}
    </button>
  )
}

function BandGrid({
  days,
  spans,
  timeZone,
  showEstablishment,
  onOpenExecution,
  columnMinRem,
}: {
  days: string[]
  spans: CalendarSpan[]
  timeZone: string
  showEstablishment: boolean
  onOpenExecution: (executionId: string) => void
  columnMinRem?: number
}) {
  const track = columnMinRem == null ? 'minmax(0, 1fr)' : `minmax(${columnMinRem}rem, 1fr)`
  return (
    <div
      data-testid="calendar-bands"
      className="relative grid min-w-0 gap-y-1 bg-white py-2"
      style={{ gridTemplateColumns: `repeat(${days.length || 1}, ${track})` }}
    >
      {spans.map((span) => (
        <BandButton
          key={span.item.id}
          span={span}
          timeZone={timeZone}
          showEstablishment={showEstablishment}
          onOpenExecution={onOpenExecution}
        />
      ))}
    </div>
  )
}

function WeekdayHeader({
  days,
  month,
  today,
  outsideMonth,
}: {
  days: string[]
  month: string
  today: string
  outsideMonth: boolean
}) {
  return (
    <div
      className="grid border-b border-[#E8E6DF]"
      style={{ gridTemplateColumns: `repeat(${days.length || 1}, minmax(0, 1fr))` }}
    >
      {days.map((day) => (
        <div
          key={day}
          data-testid={`calendar-weekday-${day}`}
          className={cn(
            'border-l border-[#E8E6DF] px-1 py-2 text-center text-xs font-semibold text-[#1a1a1a] first:border-l-0',
            outsideMonth && !day.startsWith(month) && 'bg-[#F5F4F0]',
          )}
        >
          <div className="text-[10px] uppercase text-[#57564F]">{WEEKDAY_LABELS[weekdayIndexMonday(day)]}</div>
          <div
            className={cn(
              'mx-auto mt-0.5 flex h-7 w-7 items-center justify-center rounded-full',
              day === today && 'bg-[#114660] text-white',
            )}
          >
            {Number.parseInt(day.slice(8, 10), 10)}
          </div>
        </div>
      ))}
    </div>
  )
}

function DesktopDay({
  days,
  items,
  month,
  timeZone,
  today,
  showEstablishment,
  showEmpty,
  onOpenExecution,
}: DesktopExecutionCalendarProps) {
  const day = days[0] ?? ''
  const layout = useMemo(
    () => buildDesktopDayLayout(items, day, timeZone),
    [items, day, timeZone],
  )
  return (
    <div data-testid="calendar-desktop-day" className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
      <WeekdayHeader days={[day]} month={month} today={today} outsideMonth={false} />
      {layout.count === 0 ? (
        showEmpty ? (
          <p className="px-3 py-6 text-center text-sm text-[#57564F]">Aucune exécution</p>
        ) : null
      ) : (
        <div className="flex flex-col gap-3 px-3 py-3">
          <p data-testid="calendar-desktop-day-count" className="text-sm font-semibold text-[#1a1a1a]">
            {formatCalendarExecutionCount(layout.count)}
          </p>
          {layout.groups.map((group) => (
            <section key={group.category} aria-label={CALENDAR_DAY_GROUP_LABEL[group.category]} className="flex flex-col gap-1">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[#57564F]">
                {CALENDAR_DAY_GROUP_LABEL[group.category]}
              </h3>
              {group.items.map((item) => (
                <EventCard
                  key={item.id}
                  item={item}
                  timeZone={timeZone}
                  showEstablishment={showEstablishment}
                  onOpenExecution={onOpenExecution}
                />
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  )
}

function DesktopWeek({
  days,
  items,
  timeZone,
  today,
  showEstablishment,
  showEmpty,
  onOpenExecution,
}: DesktopExecutionCalendarProps) {
  const layout = useMemo(
    () => buildDesktopWeekLayout(items, days, timeZone),
    [items, days, timeZone],
  )
  return (
    <div
      data-testid="calendar-desktop-week-scroller"
      className="min-h-0 flex-1 overflow-auto overscroll-contain"
    >
      <div
        data-testid="calendar-desktop-week-grid"
        className="grid"
        style={{
          gridTemplateColumns: `repeat(${days.length || 1}, minmax(${DESKTOP_WEEK_COLUMN_MIN_REM}rem, 1fr))`,
          minWidth: `${(days.length || 1) * DESKTOP_WEEK_COLUMN_MIN_REM}rem`,
        }}
      >
        {days.map((day, index) => (
          <div
            key={day}
            data-testid={`calendar-weekday-${day}`}
            className={cn(
              'border-b border-[#E8E6DF] px-1 py-2 text-center text-xs font-semibold text-[#1a1a1a]',
              index > 0 && 'border-l border-[#E8E6DF]',
            )}
          >
            <div className="text-[10px] uppercase text-[#57564F]">{WEEKDAY_LABELS[weekdayIndexMonday(day)]}</div>
            <div
              className={cn(
                'mx-auto mt-0.5 flex h-7 w-7 items-center justify-center rounded-full',
                day === today && 'bg-[#114660] text-white',
              )}
            >
              {Number.parseInt(day.slice(8, 10), 10)}
            </div>
          </div>
        ))}
        {layout.bands.length > 0 ? (
          <div className="min-w-0 border-b border-[#E8E6DF]" style={{ gridColumn: '1 / -1' }}>
            <BandGrid
              days={days}
              spans={layout.bands}
              timeZone={timeZone}
              showEstablishment={showEstablishment}
              onOpenExecution={onOpenExecution}
              columnMinRem={DESKTOP_WEEK_COLUMN_MIN_REM}
            />
          </div>
        ) : null}
        {layout.columns.map((column, index) => (
          <div
            key={column.day}
            data-testid={`calendar-desktop-column-${column.day}`}
            className={cn(
              'flex min-w-0 flex-col gap-1 px-1 py-1',
              index > 0 && 'border-l border-[#E8E6DF]',
            )}
          >
            {column.items.map((item) => (
              <EventCard
                key={item.id}
                item={item}
                timeZone={timeZone}
                showEstablishment={showEstablishment}
                onOpenExecution={onOpenExecution}
              />
            ))}
          </div>
        ))}
      </div>
      {showEmpty && items.length === 0 ? (
        <p className="px-3 py-6 text-center text-sm text-[#57564F]">Aucun plan sur cette période.</p>
      ) : null}
    </div>
  )
}

function DesktopMonthRow({
  row,
  month,
  timeZone,
  today,
  showEstablishment,
  onOpenExecution,
  onOpenDay,
}: {
  row: DesktopMonthRowLayout
  month: string
  timeZone: string
  today: string
  showEstablishment: boolean
  onOpenExecution: (executionId: string) => void
  onOpenDay: (anchor: string) => void
}) {
  const days = row.days.map((cell) => cell.day)
  return (
    <div className="border-b border-[#E8E6DF] last:border-b-0">
      <WeekdayHeader days={days} month={month} today={today} outsideMonth />
      {row.bands.length > 0 ? (
        <BandGrid
          days={days}
          spans={row.bands}
          timeZone={timeZone}
          showEstablishment={showEstablishment}
          onOpenExecution={onOpenExecution}
        />
      ) : null}
      <div
        className="grid"
        style={{ gridTemplateColumns: `repeat(${days.length || 1}, minmax(0, 1fr))` }}
      >
        {row.days.map((cell) => (
          <div
            key={cell.day}
            className={cn(
              'flex min-w-0 flex-col gap-0.5 border-l border-[#E8E6DF] px-1 py-1 first:border-l-0',
              !cell.day.startsWith(month) && 'bg-[#F5F4F0]',
            )}
          >
            {cell.singles.map((span) => {
              const presentation = calendarEventPresentation(span.item)
              return (
                <button
                  key={span.item.id}
                  type="button"
                  data-testid={`calendar-event-${span.item.id}`}
                  className="flex w-full min-w-0 flex-col rounded px-0.5 py-0.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#114660]"
                  style={{ color: presentation.chrome.text }}
                  aria-label={eventAccessibleLabel(span.item, timeZone, showEstablishment)}
                  onClick={() => onOpenExecution(span.item.id)}
                >
                  <EventLines
                    item={span.item}
                    timeZone={timeZone}
                    showEstablishment={showEstablishment}
                    showAssignees={false}
                  />
                </button>
              )
            })}
            {cell.overflowCount > 0 ? (
              <button
                type="button"
                data-testid={`calendar-month-overflow-${cell.day}`}
                className="w-full truncate px-0.5 py-0.5 text-left text-[11px] font-semibold text-[#114660]"
                onClick={() => onOpenDay(cell.day)}
              >
                {formatCalendarOverflowLabel(cell.overflowCount)}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}

function DesktopMonth({
  days,
  items,
  month,
  timeZone,
  today,
  showEstablishment,
  showEmpty,
  onOpenExecution,
  onOpenDay,
}: DesktopExecutionCalendarProps) {
  const rows = useMemo(() => {
    const next: DesktopMonthRowLayout[] = []
    for (let index = 0; index < days.length; index += 7) {
      next.push(buildDesktopMonthRow(items, days.slice(index, index + 7), timeZone))
    }
    return next
  }, [days, items, timeZone])
  return (
    <div
      data-testid="calendar-desktop-month"
      className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain"
    >
      {rows.map((row) => (
        <DesktopMonthRow
          key={row.days[0]?.day ?? 'empty'}
          row={row}
          month={month}
          timeZone={timeZone}
          today={today}
          showEstablishment={showEstablishment}
          onOpenExecution={onOpenExecution}
          onOpenDay={onOpenDay}
        />
      ))}
      {showEmpty && items.length === 0 ? (
        <p className="px-3 py-6 text-center text-sm text-[#57564F]">Aucun plan sur cette période.</p>
      ) : null}
    </div>
  )
}

export function DesktopExecutionCalendar(props: DesktopExecutionCalendarProps) {
  if (props.granularity === 'day') {
    return <DesktopDay {...props} />
  }
  if (props.granularity === 'week') {
    return <DesktopWeek {...props} />
  }
  return <DesktopMonth {...props} />
}
