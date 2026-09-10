import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Bell } from 'lucide-react'

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
  calendarEventAssigneeInitials,
  calendarEventAssigneeOverflow,
  calendarEventOrgBadges,
  calendarEventPresentation,
  calendarLaneStatusLabelClassName,
  calendarLaneSuiteClassName,
  calendarUnplannedCreatedDateLabel,
  resolveCalendarEventChromeDensity,
  type CalendarEventChromeDensity,
} from '../lib/execution-calendar-event-display'
import {
  isExecutionAllDay,
  isTimedDayLaneContinuation,
  occupiesAllDayLane,
  occupiesMonthCell,
  splitOverlappingColumns,
  timedIntervalOnDay,
} from '../lib/execution-calendar-layout'
import { calendarUnplannedSectionHeader } from '../lib/execution-calendar-unplanned'
import type { ExecutionCalendarGranularity } from '../lib/execution-feed-url-state'

const HOUR_HEIGHT = 48
const TIME_GRID_INITIAL_HOUR = 8
const TIME_GUTTER = '3.75rem'
const WEEKDAY_LABELS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
const MONTH_VISIBLE = 2
const ALL_DAY_VISIBLE_DAY = 2
const ALL_DAY_VISIBLE_WEEK = 1

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
  density: densityOverride,
  continuation,
  className,
  onSelect,
}: {
  item: ActionPlanExecutionFeedItem
  variant: 'timed' | 'allDay' | 'month'
  heightPx?: number
  narrow?: boolean
  density?: CalendarEventChromeDensity
  continuation?: boolean
  className?: string
  onSelect: () => void
}) {
  const density =
    densityOverride ?? resolveCalendarEventChromeDensity({ variant, heightPx, narrow })
  const presentation = calendarEventPresentation(item)
  const compact = density === 'compact'
  const lane = density === 'lane'
  const showSuite = continuation === true && (lane || !compact)
  const showMetaLayers = !lane
  return (
    <button
      type="button"
      className={cn(
        'flex min-w-[2.75rem] items-stretch justify-start overflow-hidden rounded-md border border-black/5 text-left leading-tight',
        compact ? 'min-h-8' : 'min-h-7',
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
      <span
        className={cn(
          'flex min-h-0 min-w-0 flex-1 overflow-hidden px-1.5 py-0.5',
          lane ? 'flex-row items-center gap-1' : 'flex-col items-start justify-start',
          !lane && (compact ? 'gap-px' : 'gap-0.5'),
        )}
      >
        <span
          className={cn(
            'flex min-w-0 items-baseline gap-1',
            lane ? 'min-w-0 flex-1 text-[10px]' : 'w-full',
            !lane && (compact ? 'text-[10px]' : 'text-[11px]'),
          )}
        >
          <span className={cn('min-w-0 font-semibold', compact || lane ? 'line-clamp-1' : 'line-clamp-2')}>
            {presentation.title}
          </span>
          {showSuite ? (
            <span className={lane ? calendarLaneSuiteClassName() : 'shrink-0 text-[9px] font-medium opacity-70'}>
              Suite
            </span>
          ) : null}
        </span>
        {showMetaLayers && presentation.orgBadges.length > 0 ? (
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
        {showMetaLayers &&
        (presentation.assigneeInitials.length > 0 || presentation.assigneeOverflow > 0) ? (
          <span className="flex min-w-0 items-center">
            {presentation.assigneeInitials.map((initials, index) => (
              <span
                key={`${initials}-${index}`}
                className={cn(
                  'flex shrink-0 items-center justify-center rounded-full bg-[#3A7A96] font-bold text-white ring-1 ring-white',
                  compact ? 'h-3.5 w-3.5 text-[7px]' : 'h-4 w-4 text-[8px]',
                  index > 0 && '-ml-1',
                )}
                aria-hidden
              >
                {initials}
              </span>
            ))}
            {presentation.assigneeOverflow > 0 ? (
              <span className={cn('ml-0.5 font-semibold opacity-80', compact ? 'text-[8px]' : 'text-[10px]')}>
                +{presentation.assigneeOverflow}
              </span>
            ) : null}
          </span>
        ) : null}
        <span
          className={cn(
            'flex min-w-0 items-center gap-1 font-medium opacity-80',
            lane && 'shrink-0',
            compact || lane ? 'text-[9px]' : 'text-[10px]',
          )}
        >
          {item.status === 'pending_validation' ? (
            <Bell
              className={cn('shrink-0', compact || lane ? 'h-2.5 w-2.5' : 'h-3 w-3')}
              style={{ color: presentation.chrome.bar }}
              aria-hidden
            />
          ) : (
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: presentation.chrome.bar }}
              aria-hidden
            />
          )}
          <span className={lane ? calendarLaneStatusLabelClassName() : 'truncate'}>
            {presentation.statusLabel}
          </span>
        </span>
      </span>
    </button>
  )
}

function allDayLaneVisibleLimit(dayCount: number): number {
  return dayCount > 1 ? ALL_DAY_VISIBLE_WEEK : ALL_DAY_VISIBLE_DAY
}

function AllDayLane({
  days,
  items,
  onOpenExecution,
  onOpenOverflow,
}: {
  days: string[]
  items: ActionPlanExecutionFeedItem[]
  onOpenExecution: (executionId: string) => void
  onOpenOverflow: (day: string) => void
}) {
  const hasOccupants = days.some((day) => items.some((item) => occupiesAllDayLane(item, day)))
  if (!hasOccupants) {
    return null
  }
  const visibleLimit = allDayLaneVisibleLimit(days.length)
  return (
    <div
      data-testid="calendar-all-day-lane"
      className="grid shrink-0 border-b border-[#E8E6DF] bg-white"
      style={{ gridTemplateColumns: `${TIME_GUTTER} repeat(${days.length}, minmax(0, 1fr))` }}
    >
      <div className="px-1 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#7D7B75]">
        Journée
      </div>
      {days.map((day) => {
        const dayItems = items.filter((item) => occupiesAllDayLane(item, day))
        const visible = dayItems.slice(0, visibleLimit)
        const extra = dayItems.length - visible.length
        return (
          <div key={day} className="flex flex-col gap-0.5 border-l border-[#E8E6DF] px-1 py-1">
            {visible.map((item) => (
              <CalendarEventButton
                key={item.id}
                item={item}
                variant="allDay"
                continuation={isTimedDayLaneContinuation(item, day)}
                onSelect={() => onOpenExecution(item.id)}
              />
            ))}
            {extra > 0 ? (
              <button
                type="button"
                className="text-left text-[10px] font-semibold text-[#114660]"
                onClick={() => onOpenOverflow(day)}
              >
                +{extra} de plus
              </button>
            ) : null}
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
    <div className="grid" style={{ gridTemplateColumns: `${TIME_GUTTER} repeat(${days.length}, minmax(0, 1fr))` }}>
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

function CalendarDayOverflowSheet({
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
            density="comfortable"
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
  const [unplannedExpanded, setUnplannedExpanded] = useState(false)
  const didAlignTimeGridRef = useRef(false)
  const items = data ? unwrapActionPlanExecutionFeedItems(data.items) : []
  const unplanned = data ? unwrapActionPlanExecutionFeedItems(data.unplanned) : []
  const overflowItems = useMemo(() => {
    if (!overflowDay) {
      return []
    }
    const occupiesOverflow =
      granularity === 'month' ? occupiesMonthCell : occupiesAllDayLane
    return items.filter((item) => occupiesOverflow(item, overflowDay))
  }, [granularity, items, overflowDay])

  useLayoutEffect(() => {
    if (granularity === 'month') {
      didAlignTimeGridRef.current = false
    }
  }, [granularity])

  const attachTimeScroller = useCallback((node: HTMLDivElement | null) => {
    if (!node || didAlignTimeGridRef.current) {
      return
    }
    node.scrollTop = TIME_GRID_INITIAL_HOUR * HOUR_HEIGHT
    didAlignTimeGridRef.current = true
  }, [])

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
      style={{ gridTemplateColumns: granularity === 'day' ? `${TIME_GUTTER} 1fr` : `${TIME_GUTTER} repeat(${days.length}, minmax(4.5rem, 1fr))` }}
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
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
        <div
          data-testid="calendar-month-scroller"
          className="min-h-0 flex-1 overflow-y-auto"
        >
          <div
            data-testid="calendar-month-grid"
            className="overflow-hidden rounded-xl border border-[#E8E6DF] bg-white"
          >
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
                const dayItems = items.filter((item) => occupiesMonthCell(item, day))
                const visible = dayItems.slice(0, MONTH_VISIBLE)
                const extra = dayItems.length - visible.length
                const inMonth = day.startsWith(month)
                return (
                  <div
                    key={day}
                    className={cn(
                      'min-h-[6.5rem] border-l border-[#E8E6DF] px-1 py-1 first:border-l-0',
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
        </div>
        <UnplannedBanner
          items={unplanned}
          expanded={unplannedExpanded}
          onToggle={() => setUnplannedExpanded((current) => !current)}
          onOpenExecution={onOpenExecution}
        />
        <CalendarDayOverflowSheet
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
    <div
      data-testid="calendar-hub-scroller"
      className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden"
    >
      <div
        data-testid="calendar-grid-card"
        className={cn(
          'flex min-h-0 flex-1 flex-col rounded-xl border border-[#E8E6DF] bg-white',
          granularity === 'week'
            ? 'overflow-x-auto overflow-y-hidden overscroll-x-contain'
            : 'overflow-hidden',
        )}
      >
        <div
          className={cn(
            'flex min-h-0 min-w-0 flex-1 flex-col',
            granularity === 'week' && 'min-w-[44rem]',
          )}
        >
          {header}
          <AllDayLane
            days={days}
            items={items}
            onOpenExecution={onOpenExecution}
            onOpenOverflow={setOverflowDay}
          />
          <div
            ref={attachTimeScroller}
            data-testid="calendar-time-scroller"
            className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain"
          >
            <TimeGrid days={days} items={items} onOpenExecution={onOpenExecution} />
          </div>
        </div>
      </div>
      <UnplannedBanner
        items={unplanned}
        expanded={unplannedExpanded}
        onToggle={() => setUnplannedExpanded((current) => !current)}
        onOpenExecution={onOpenExecution}
      />
      <CalendarDayOverflowSheet
        day={overflowDay ?? ''}
        items={overflowItems}
        open={overflowDay != null}
        onClose={() => setOverflowDay(null)}
        onOpenExecution={onOpenExecution}
      />
    </div>
  )
}

function UnplannedBanner({
  items,
  expanded,
  onToggle,
  onOpenExecution,
}: {
  items: ActionPlanExecutionFeedItem[]
  expanded: boolean
  onToggle: () => void
  onOpenExecution: (executionId: string) => void
}) {
  if (items.length === 0) {
    return null
  }
  const header = calendarUnplannedSectionHeader(items)
  return (
    <TerrainCollapsibleFeedSection
      className="shrink-0"
      label={header.label}
      count={header.count}
      dotVariant={header.dotVariant}
      expanded={expanded}
      onToggle={onToggle}
    >
      <div
        data-testid="calendar-unplanned-list"
        className="flex max-h-48 flex-col gap-1 overflow-y-auto overscroll-y-contain"
      >
        {items.map((item) => {
          const orgBadges = calendarEventOrgBadges(item)
          const initials = calendarEventAssigneeInitials(item.assignees)
          const overflow = calendarEventAssigneeOverflow(item.assignees)
          const createdDate = calendarUnplannedCreatedDateLabel(item.created_at)
          return (
            <button
              key={item.id}
              type="button"
              className="rounded-xl border border-[#E8E6DF] bg-white px-3 py-2 text-left text-[#1a1a1a]"
              onClick={() => onOpenExecution(item.id)}
            >
              <span className="block truncate text-sm font-semibold">{item.title}</span>
              {orgBadges.length > 0 ? (
                <span className="mt-0.5 flex min-w-0 flex-wrap gap-0.5">
                  {orgBadges.map((badge) => (
                    <span
                      key={badge}
                      className="max-w-full truncate rounded bg-[#F5F4EF] px-1 py-px text-[10px] font-semibold"
                    >
                      {badge}
                    </span>
                  ))}
                </span>
              ) : null}
              {initials.length > 0 || overflow > 0 ? (
                <span className="mt-1 flex min-w-0 items-center">
                  {initials.map((label, index) => (
                    <span
                      key={`${label}-${index}`}
                      className={cn(
                        'flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#3A7A96] text-[8px] font-bold text-white ring-1 ring-white',
                        index > 0 && '-ml-1',
                      )}
                      aria-hidden
                    >
                      {label}
                    </span>
                  ))}
                  {overflow > 0 ? (
                    <span className="ml-0.5 text-[10px] font-semibold text-[#7D7B75]">+{overflow}</span>
                  ) : null}
                </span>
              ) : null}
              {createdDate ? (
                <span className="mt-1 block truncate text-[11px] font-medium text-[#7D7B75]">
                  {createdDate}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
    </TerrainCollapsibleFeedSection>
  )
}
