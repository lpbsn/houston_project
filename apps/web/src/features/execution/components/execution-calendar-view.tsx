import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent,
} from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import { TerrainCollapsibleFeedSection, TerrainErrorState } from '@/components/ui/terrain'
import { todayCivilDate, BUSINESS_TIMEZONE } from '@/lib/business-timezone'
import { cn } from '@/lib/utils'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import type {
  ActionPlanExecutionCalendarResponse,
  ActionPlanExecutionFeedItem,
} from '@/features/action-plans/types'
import { resolveApiErrorMessage } from '@/lib/error-message'

import { DesktopExecutionCalendar } from './execution-calendar-desktop-view'
import {
  calendarEventEstablishmentLabel,
  calendarEventPilotLabel,
  calendarEventPresentation,
  calendarUnplannedCreatedDateLabel,
} from '../lib/execution-calendar-event-display'
import { buildCalendarSpansFromPlaced, placeCalendarItems } from '../lib/execution-calendar-layout'
import { calendarUnplannedSectionHeader } from '../lib/execution-calendar-unplanned'
import {
  initialWeekStartIndex,
  shiftWeekStartIndex,
  sliceVisibleWeekDays,
  weekVisibleDayCount,
} from '../lib/execution-calendar-visible-days'
import { useDesktopCalendarSurface } from '../lib/execution-calendar-surface'
import type { ExecutionCalendarGranularity } from '../lib/execution-feed-url-state'
import { calendarWeekdayLabel } from '../lib/execution-calendar-window'

const WEEK_SWIPE_MIN_DX = 48
const WEEK_SWIPE_CLICK_SUPPRESS_MS = 50

type ExecutionCalendarViewProps = {
  granularity: ExecutionCalendarGranularity
  days: string[]
  month: string
  data?: ActionPlanExecutionCalendarResponse
  timeZone?: string
  isLoading: boolean
  isError: boolean
  error: unknown
  onRetry: () => void
  onOpenExecution: (executionId: string) => void
  onOpenDay?: (anchor: string) => void
  showEstablishment?: boolean
  onDeadlineDrop?: (executionId: string, date: string) => void
}

/** One CSS grid item per execution, spanning all occupied civil days in this row. */
function CalendarBands({
  days,
  placed,
  showEstablishment,
  onOpenExecution,
}: {
  days: string[]
  placed: ReturnType<typeof placeCalendarItems>
  showEstablishment: boolean
  onOpenExecution: (executionId: string) => void
}) {
  const spans = useMemo(() => buildCalendarSpansFromPlaced(placed, days), [placed, days])
  return (
    <div
      data-testid="calendar-bands"
      className="relative grid min-h-24 gap-y-2 bg-white py-3"
      style={{ gridTemplateColumns: `repeat(${days.length || 1}, minmax(0, 1fr))` }}
    >
      <div className="pointer-events-none absolute inset-0 grid" aria-hidden
        style={{ gridTemplateColumns: `repeat(${days.length || 1}, minmax(0, 1fr))` }}>
        {days.map((day) => <div key={day} className="border-l border-[#E8E6DF] first:border-l-0" />)}
      </div>
      {spans.map((span) => {
        const presentation = calendarEventPresentation(span.item)
        const pilot = calendarEventPilotLabel(span.item)
        const establishment = showEstablishment ? calendarEventEstablishmentLabel(span.item) : ''
        const names = span.item.assignees.map((assignee) => assignee.display_name).join(', ')
        const label = [presentation.title, presentation.statusLabel, pilot, establishment, names,
          span.continuesBefore ? 'Commencé avant cette période' : '',
          span.continuesAfter ? 'Se poursuit après cette période' : '',
        ].filter(Boolean).join(' · ')
        return (
          <button
            key={span.item.id}
            type="button"
            data-testid={`calendar-span-${span.item.id}`}
            data-continues-before={span.continuesBefore || undefined}
            data-continues-after={span.continuesAfter || undefined}
            className={cn(
              'relative z-10 mx-1 flex min-h-10 min-w-0 items-center gap-1 overflow-hidden rounded-lg border border-black/10 px-2 py-1.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#114660]',
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
            title={label}
            onClick={() => onOpenExecution(span.item.id)}
          >
            {span.continuesBefore ? <ChevronLeft className="h-3 w-3 shrink-0" aria-hidden /> : null}
            <span className="min-w-0 flex-1 truncate text-xs font-semibold">{presentation.title}</span>
            {pilot ? <span className="sr-only">{pilot}</span> : null}
            {establishment ? (
              <span
                data-testid={`calendar-establishment-${span.item.id}`}
                className="min-w-0 max-w-[40%] truncate text-[11px] font-medium"
              >
                {establishment}
              </span>
            ) : null}
            {span.endColumn > span.startColumn || days.length === 1 ? (
              <span className="hidden min-w-0 max-w-[40%] truncate text-[11px] lg:block">
                {[names, presentation.statusLabel].filter(Boolean).join(' · ')}
              </span>
            ) : null}
            {span.continuesAfter ? <ChevronRight className="h-3 w-3 shrink-0" aria-hidden /> : null}
          </button>
        )
      })}
    </div>
  )
}

function WeekWindowControls({
  canGoBack,
  canGoForward,
  onBack,
  onForward,
}: {
  canGoBack: boolean
  canGoForward: boolean
  onBack: () => void
  onForward: () => void
}) {
  return (
    <div className="flex h-full items-center justify-center gap-0">
      <button
        type="button"
        data-testid="calendar-week-prev-days"
        className="rounded p-0.5 text-[#7D7B75] disabled:opacity-30"
        aria-label="Jours précédents de la semaine"
        disabled={!canGoBack}
        onClick={onBack}
      >
        <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
      </button>
      <button
        type="button"
        data-testid="calendar-week-next-days"
        className="rounded p-0.5 text-[#7D7B75] disabled:opacity-30"
        aria-label="Jours suivants de la semaine"
        disabled={!canGoForward}
        onClick={onForward}
      >
        <ChevronRight className="h-3.5 w-3.5" aria-hidden />
      </button>
    </div>
  )
}

function CalendarPeriodStatus({
  isPeriodPending,
  isTransitionError,
  error,
  onRetry,
}: {
  isPeriodPending: boolean
  isTransitionError: boolean
  error: unknown
  onRetry: () => void
}) {
  if (isPeriodPending) {
    return (
      <p
        data-testid="calendar-period-pending"
        role="status"
        aria-live="polite"
        className="shrink-0 px-1 py-1.5 text-center text-xs font-medium text-[#7D7B75]"
      >
        Chargement des événements…
      </p>
    )
  }
  if (isTransitionError) {
    return (
      <div data-testid="calendar-period-error" className="shrink-0">
        <TerrainErrorState
          message={resolveApiErrorMessage(
            error,
            ActionPlansApiError,
            'Impossible de charger le calendrier.',
          )}
          onRetry={onRetry}
        />
      </div>
    )
  }
  return null
}

export function ExecutionCalendarView({
  granularity,
  days,
  month,
  data,
  timeZone: timeZoneProp,
  isLoading,
  isError,
  error,
  onRetry,
  onOpenExecution,
  onOpenDay,
  showEstablishment = false,
  onDeadlineDrop,
}: ExecutionCalendarViewProps) {
  const timeZone = timeZoneProp ?? data?.timezone ?? BUSINESS_TIMEZONE
  const today = todayCivilDate(timeZone)
  const desktopCalendar = useDesktopCalendarSurface()
  const daysKey = days.join(',')
  const weekVisibleCount = weekVisibleDayCount(days.length)
  const compactWeek = granularity === 'week' && weekVisibleCount < days.length
  const weekWindowKey = `${daysKey}|${today}|${weekVisibleCount}`
  const [weekWindow, setWeekWindow] = useState(() => ({
    key: weekWindowKey,
    startIndex: initialWeekStartIndex({ days, today, visibleCount: weekVisibleCount }),
  }))
  const swipeOriginRef = useRef<{ x: number; y: number } | null>(null)
  const suppressWeekClickRef = useRef(false)
  const suppressWeekClickTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [unplannedExpanded, setUnplannedExpanded] = useState(false)
  const [hasShownCalendar, setHasShownCalendar] = useState(false)
  const shownCalendar = hasShownCalendar || data != null
  if (shownCalendar && !hasShownCalendar) {
    setHasShownCalendar(true)
  }
  const items = useMemo(
    () => (data ? unwrapActionPlanExecutionFeedItems(data.items) : []),
    [data],
  )
  const placed = useMemo(() => placeCalendarItems(items, timeZone), [items, timeZone])
  const unplanned = useMemo(
    () => (data ? unwrapActionPlanExecutionFeedItems(data.unplanned) : []),
    [data],
  )
  let weekStartIndex = weekWindow.startIndex
  if (weekWindow.key !== weekWindowKey) {
    weekStartIndex = initialWeekStartIndex({ days, today, visibleCount: weekVisibleCount })
    setWeekWindow({ key: weekWindowKey, startIndex: weekStartIndex })
  }

  const gridDays =
    granularity === 'week'
      ? sliceVisibleWeekDays(days, weekStartIndex, weekVisibleCount)
      : days
  const maxWeekStart = Math.max(0, days.length - weekVisibleCount)
  const shiftVisibleWeek = useCallback(
    (delta: -1 | 1) => {
      setWeekWindow((current) => {
        const baseStart =
          current.key === weekWindowKey
            ? current.startIndex
            : initialWeekStartIndex({ days, today, visibleCount: weekVisibleCount })
        return {
          key: weekWindowKey,
          startIndex: shiftWeekStartIndex(baseStart, delta, days.length, weekVisibleCount),
        }
      })
    },
    [days, today, weekVisibleCount, weekWindowKey],
  )

  const onWeekPointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!compactWeek) {
        return
      }
      swipeOriginRef.current = { x: event.clientX, y: event.clientY }
    },
    [compactWeek],
  )

  const onWeekPointerUp = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      const origin = swipeOriginRef.current
      swipeOriginRef.current = null
      if (!compactWeek || !origin) {
        return
      }
      const dx = event.clientX - origin.x
      const dy = event.clientY - origin.y
      if (Math.abs(dx) < WEEK_SWIPE_MIN_DX || Math.abs(dx) <= Math.abs(dy)) {
        return
      }
      shiftVisibleWeek(dx < 0 ? 1 : -1)
      suppressWeekClickRef.current = true
      if (suppressWeekClickTimeoutRef.current != null) {
        window.clearTimeout(suppressWeekClickTimeoutRef.current)
      }
      suppressWeekClickTimeoutRef.current = window.setTimeout(() => {
        suppressWeekClickRef.current = false
        suppressWeekClickTimeoutRef.current = null
      }, WEEK_SWIPE_CLICK_SUPPRESS_MS)
    },
    [compactWeek, shiftVisibleWeek],
  )

  const onWeekClickCapture = useCallback((event: MouseEvent<HTMLDivElement>) => {
    if (!suppressWeekClickRef.current) {
      return
    }
    event.preventDefault()
    event.stopPropagation()
    suppressWeekClickRef.current = false
    if (suppressWeekClickTimeoutRef.current != null) {
      window.clearTimeout(suppressWeekClickTimeoutRef.current)
      suppressWeekClickTimeoutRef.current = null
    }
  }, [])

  const isInitialLoading = isLoading && !shownCalendar
  const isPeriodPending = isLoading && shownCalendar
  const isInitialError = isError && data == null && !shownCalendar
  const isTransitionError = isError && data == null && shownCalendar

  if (isInitialLoading) {
    return <p className="px-1 py-8 text-center text-sm text-[#7D7B75]">Chargement du calendrier…</p>
  }

  if (isInitialError) {
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

  const periodStatus = (
    <CalendarPeriodStatus
      isPeriodPending={isPeriodPending}
      isTransitionError={isTransitionError}
      error={error}
      onRetry={onRetry}
    />
  )

  const weeks: string[][] = []
  if (granularity === 'month') {
    for (let index = 0; index < days.length; index += 7) weeks.push(days.slice(index, index + 7))
  } else {
    weeks.push(gridDays)
  }

  const gridCardClassName = 'flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[#E8E6DF] bg-white'

  return (
    <div data-testid="calendar-hub-scroller" className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden" aria-busy={isPeriodPending}>
      {periodStatus}
      {desktopCalendar ? (
        <div data-testid="calendar-grid-card" className={gridCardClassName}>
          <DesktopExecutionCalendar
            onDeadlineDrop={onDeadlineDrop}
            granularity={granularity}
            days={days}
            month={month}
            items={items}
            placed={placed}
            timeZone={timeZone}
            today={today}
            showEstablishment={showEstablishment}
            showEmpty={!isPeriodPending && !isTransitionError}
            onOpenExecution={onOpenExecution}
            onOpenDay={onOpenDay ?? (() => undefined)}
          />
        </div>
      ) : (
      <div
        data-testid="calendar-grid-card"
        className={cn(gridCardClassName, 'touch-pan-y')}
        onPointerDown={onWeekPointerDown}
        onPointerUp={onWeekPointerUp}
        onClickCapture={onWeekClickCapture}
        onPointerCancel={() => { swipeOriginRef.current = null }}
      >
        {compactWeek ? (
          <div className="flex shrink-0 justify-end border-b border-[#E8E6DF] p-1">
            <WeekWindowControls canGoBack={weekStartIndex > 0} canGoForward={weekStartIndex < maxWeekStart}
              onBack={() => shiftVisibleWeek(-1)} onForward={() => shiftVisibleWeek(1)} />
          </div>
        ) : null}
        <div data-testid={granularity === 'month' ? 'calendar-month-scroller' : 'calendar-date-scroller'}
          className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
          <div data-testid={granularity === 'month' ? 'calendar-month-grid' : undefined}>
            {weeks.map((week) => (
              <div key={week[0]} className="border-b border-[#E8E6DF] last:border-b-0">
                <div className="grid border-b border-[#E8E6DF]" style={{ gridTemplateColumns: `repeat(${week.length || 1}, minmax(0, 1fr))` }}>
                  {week.map((day) => (
                    <div key={day} data-testid={`calendar-weekday-${day}`} className={cn(
                      'border-l border-[#E8E6DF] px-1 py-2 text-center text-xs font-semibold text-[#1a1a1a] first:border-l-0',
                      granularity === 'month' && !day.startsWith(month) && 'bg-[#F5F4F0]',
                    )}>
                      <div className="text-[10px] uppercase text-[#57564F]">{calendarWeekdayLabel(day)}</div>
                      <div className={cn('mx-auto mt-0.5 flex h-7 w-7 items-center justify-center rounded-full', day === today && 'bg-[#114660] text-white')}>
                        {Number.parseInt(day.slice(8, 10), 10)}
                      </div>
                    </div>
                  ))}
                </div>
                <CalendarBands
                  days={week}
                  placed={placed}
                  showEstablishment={showEstablishment}
                  onOpenExecution={onOpenExecution}
                />
              </div>
            ))}
          </div>
          {!isPeriodPending && !isTransitionError && items.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-[#57564F]">Aucun plan sur cette période.</p>
          ) : null}
        </div>
      </div>
      )}
      <UnplannedBanner
        items={unplanned}
        expanded={unplannedExpanded}
        showEstablishment={showEstablishment}
        onToggle={() => setUnplannedExpanded((current) => !current)}
        onOpenExecution={onOpenExecution}
      />
    </div>
  )
}

function UnplannedBanner({
  items,
  expanded,
  showEstablishment,
  onToggle,
  onOpenExecution,
}: {
  items: ActionPlanExecutionFeedItem[]
  expanded: boolean
  showEstablishment: boolean
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
          const { orgBadges, assigneeInitials: initials, assigneeOverflow: overflow } =
            calendarEventPresentation(item)
          const createdDate = calendarUnplannedCreatedDateLabel(item.created_at)
          const establishment = showEstablishment ? calendarEventEstablishmentLabel(item) : ''
          return (
            <button
              key={item.id}
              type="button"
              className="rounded-xl border border-[#E8E6DF] bg-white px-3 py-2 text-left text-[#1a1a1a]"
              onClick={() => onOpenExecution(item.id)}
            >
              <span className="block truncate text-sm font-semibold">{item.title}</span>
              {establishment ? (
                <span
                  data-testid={`calendar-establishment-${item.id}`}
                  className="mt-0.5 block truncate text-[11px] font-medium text-[#57564F]"
                >
                  {establishment}
                </span>
              ) : null}
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
