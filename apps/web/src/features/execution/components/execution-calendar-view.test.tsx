// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { installTestMatchMedia, testMediaMatches } from '@/test/viewport-match-media'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { ActionPlansApiError } from '@/features/action-plans/api'
import { combineCivilDateTimeToIso } from '@/lib/business-timezone'
import * as businessTimezone from '@/lib/business-timezone'
import { collectOverflowYScrollElements } from '@/lib/terrain-scroll-layout'

import { ExecutionCalendarView } from './execution-calendar-view'
import { resolveCalendarWindow } from '../lib/execution-calendar-window'

const MONDAY_WEEK = [
  '2026-09-07',
  '2026-09-08',
  '2026-09-09',
  '2026-09-10',
  '2026-09-11',
  '2026-09-12',
  '2026-09-13',
] as const

function wrap(item: Partial<ActionPlanExecutionFeedItem> & { id: string; title: string }) {
  return {
    item_type: 'action_plan_execution' as const,
    action_plan_execution: {
      description_short: '',
      status: 'in_progress',
      requires_validation: false,
      validated_at: null,
      pilot_business_unit: {
        id: 'bu-1',
        specific_name: 'Restaurant',
        instance_description: '',
        active: true,
        generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
      },
      involved_poles: [],
      signal_summary: null,
      assignees: [],
      start_at: '2026-09-08T07:00:00.000Z',
      end_at: '2026-09-08T09:00:00.000Z',
      all_day: false,
      is_overdue: false,
      task_count: 0,
      treated_task_count: 0,
      task_executions: [],
      last_activity_at: '2026-09-08T08:00:00.000Z',
      created_at: '2026-09-08T08:00:00.000Z',
      is_pinned: false,
      permission_hints: {
        can_mark_done: false,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_update: false,
        is_pilot_pole_assignee: false,
        can_pin: false,
      },
      ...item,
    } as ActionPlanExecutionFeedItem,
  }
}

const emptyCalendarData = {
  timezone: 'Europe/Paris' as const,
  items: [] as ReturnType<typeof wrap>[],
  unplanned: [] as ReturnType<typeof wrap>[],
}

function mockToday(date: string) {
  vi.spyOn(businessTimezone, 'todayCivilDate').mockReturnValue(date)
}

function stubMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: testMediaMatches(query, matches),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function visibleWeekDays() {
  return MONDAY_WEEK.filter((day) => screen.queryByTestId(`calendar-weekday-${day}`))
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
  vi.useRealTimers()
  Reflect.deleteProperty(window, 'matchMedia')
})

describe('ExecutionCalendarView', () => {
  it('keeps overlapping plans independently clickable', () => {
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-a',
              title: 'Créneau A',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
            wrap({
              id: 'exec-b',
              title: 'Créneau B',
              start_at: '2026-09-08T07:30:00.000Z',
              end_at: '2026-09-08T09:30:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Créneau A/ }))
    fireEvent.click(screen.getByRole('button', { name: /Créneau B/ }))
    expect(onOpen).toHaveBeenCalledWith('exec-a')
    expect(onOpen).toHaveBeenCalledWith('exec-b')
  })

  it('keeps unplanned collapsed outside the date-only scroller', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-timed',
              title: 'Brief cuisine',
              status: 'in_progress',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
              assignees: [{ membership_id: 'm-1', display_name: 'Alice Martin' }],
            }),
            wrap({
              id: 'exec-all-day',
              title: 'Inventaire',
              all_day: true,
              start_at: '2026-09-08T00:00:00.000Z',
              end_at: '2026-09-08T23:59:59.000Z',
            }),
          ],
          unplanned: [
            wrap({
              id: 'exec-unplanned',
              title: 'Sans créneau',
              start_at: null,
              end_at: null,
            }),
          ],
        }}
      />,
    )

    const unplannedToggle = screen.getByRole('button', { name: 'Déplier la section Non planifiés' })
    expect(unplannedToggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByText('Non planifiés · 1')).toBeTruthy()
    expect(screen.queryByText('Sans créneau')).toBeNull()

    const gridCard = screen.getByTestId('calendar-grid-card')
    expect(
      gridCard.compareDocumentPosition(unplannedToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()

    const scroller = screen.getByTestId('calendar-date-scroller')
    expect(scroller.scrollTop).toBe(0)
    expect(scroller.textContent).not.toContain('00:00')
    expect(screen.queryByText('Journée')).toBeNull()
    expect(screen.getByRole('button', { name: /Brief cuisine/ }).textContent).toContain('En cours')
    const allDayChip = screen.getByRole('button', { name: /Inventaire/ })
    expect(allDayChip.textContent).toContain('En cours')
    expect(allDayChip.textContent).toContain('Restaurant')
    expect(scroller.contains(allDayChip)).toBe(true)
  })

  it('keeps unplanned pending_validation collapsed and names them on the header', () => {
    render(
      <ExecutionCalendarView
        granularity="week"
        days={['2026-09-07', '2026-09-08', '2026-09-09']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [],
          unplanned: [
            wrap({
              id: 'exec-pending-unplanned',
              title: 'Nouvelle fuite sous le lave-vaisselle',
              status: 'pending_validation',
              start_at: null,
              end_at: '2026-08-29T08:00:00.000Z',
            }),
            wrap({
              id: 'exec-done-unplanned',
              title: 'Ancien plan sans date',
              status: 'done',
              start_at: null,
            }),
          ],
        }}
      />,
    )

    const unplannedToggle = screen.getByRole('button', {
      name: 'Déplier la section Non planifiés · 1 à valider',
    })
    expect(unplannedToggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByText('Non planifiés · 1 à valider · 2')).toBeTruthy()
    expect(screen.queryByText('Nouvelle fuite sous le lave-vaisselle')).toBeNull()
    expect(screen.queryByText('Ancien plan sans date')).toBeNull()
    expect(screen.queryByRole('button', { name: /Nouvelle fuite/ })).toBeNull()
  })

  it('renders scheduled and pending_validation plans on the day grid', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-scheduled',
              title: 'Brief planifié',
              status: 'scheduled',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T08:00:00.000Z',
            }),
            wrap({
              id: 'exec-pending',
              title: 'Brief à valider',
              status: 'pending_validation',
              start_at: '2026-09-08T09:00:00.000Z',
              end_at: '2026-09-08T10:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const scheduled = screen.getByRole('button', { name: /Brief planifié/ })
    const pending = screen.getByRole('button', { name: /Brief à valider/ })
    expect(scheduled.textContent).toContain('Planifié')
    expect(scheduled.getAttribute('aria-label')).toContain('Planifié')
    expect(pending.textContent).toContain('À valider')
    expect(pending.getAttribute('aria-label')).toContain('À valider')
  })

  it('keeps status and org on month chips', () => {
    render(
      <ExecutionCalendarView
        granularity="month"
        days={['2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-month',
              title: 'Brief cuisine',
              status: 'in_progress',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const chip = screen.getByRole('button', { name: /Brief cuisine/ })
    expect(chip.getAttribute('aria-label')).toContain('En cours')
    expect(chip.textContent).toContain('Restaurant')
  })

  it('keeps the month grid in the same scroller when unplanned is expanded', () => {
    render(
      <ExecutionCalendarView
        granularity="month"
        days={['2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-month',
              title: 'Brief cuisine',
              status: 'in_progress',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [
            wrap({
              id: 'exec-unplanned',
              title: 'Sans créneau',
              start_at: null,
              end_at: null,
            }),
          ],
        }}
      />,
    )

    const scroller = screen.getByTestId('calendar-month-scroller')
    const grid = screen.getByTestId('calendar-month-grid')
    const unplannedToggle = screen.getByRole('button', { name: 'Déplier la section Non planifiés' })
    expect(scroller.contains(grid)).toBe(true)
    expect(scroller.contains(unplannedToggle)).toBe(false)
    expect(
      grid.compareDocumentPosition(unplannedToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.getByText('lun.')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()
    expect(screen.queryByText('Sans créneau')).toBeNull()

    fireEvent.click(unplannedToggle)

    expect(screen.getByTestId('calendar-month-grid')).toBe(grid)
    expect(scroller.contains(grid)).toBe(true)
    expect(scroller.contains(screen.getByRole('button', { name: /Sans créneau/ }))).toBe(false)
    expect(screen.getByText('lun.')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()
    expect(collectOverflowYScrollElements(scroller)).toEqual([])
  })

  it('renders one continuous execution button across the visible week', () => {
    mockToday('2026-09-08')
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="week"
        days={['2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13', '2026-09-14']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-span',
              title: 'Chantier toiture',
              start_at: combineCivilDateTimeToIso('2026-09-08', '14:00'),
              end_at: combineCivilDateTimeToIso('2026-09-13', '15:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const chips = screen.getAllByRole('button', { name: /Chantier toiture/ })
    expect(chips).toHaveLength(1)
    expect(chips[0].getAttribute('data-continues-after')).toBe('true')
    fireEvent.click(chips[0])
    fireEvent.click(chips[chips.length - 1])
    expect(onOpen).toHaveBeenCalledWith('exec-span')
    expect(onOpen).toHaveBeenCalledTimes(2)
  })

  it('does not label Suite on a full first civil day in the day lane', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-full-start',
              title: 'Ouverture site',
              start_at: combineCivilDateTimeToIso('2026-09-08', '00:00'),
              end_at: combineCivilDateTimeToIso('2026-09-13', '15:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const chip = screen.getByRole('button', { name: /Ouverture site/ })
    expect(chip.textContent).not.toContain('Suite')
    expect(screen.getByTestId('calendar-date-scroller').contains(chip)).toBe(true)
  })

  it('renders a multi-day execution once per month row', () => {
    render(
      <ExecutionCalendarView
        granularity="month"
        days={['2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-month-span',
              title: 'Chantier toiture',
              start_at: combineCivilDateTimeToIso('2026-09-08', '14:00'),
              end_at: combineCivilDateTimeToIso('2026-09-13', '15:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    expect(screen.getAllByRole('button', { name: /Chantier toiture/ })).toHaveLength(1)
    expect(screen.getByTestId('calendar-span-exec-month-span').style.gridColumn).toBe('2 / 8')
    expect(screen.queryByText('Suite')).toBeNull()
  })

  it('shows compact unplanned facts without list-card chrome', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [],
          unplanned: [
            wrap({
              id: 'exec-unplanned',
              title: 'Sans créneau',
              start_at: null,
              end_at: null,
              created_at: '2026-09-08T08:00:00.000Z',
              assignees: [{ membership_id: 'm-1', display_name: 'Alice Martin' }],
            }),
          ],
        }}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Non planifiés' }))
    const card = screen.getByRole('button', { name: /Sans créneau/ })
    const createdLabel = `Créé le ${new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    }).format(new Date('2026-09-08T12:00:00.000Z'))}`
    expect(card.textContent).toContain('Restaurant')
    expect(card.textContent).toContain('AM')
    expect(card.textContent).toContain(createdLabel)
    expect(card.textContent?.indexOf('AM') ?? -1).toBeLessThan(card.textContent?.indexOf(createdLabel) ?? -1)
    expect(card.textContent).not.toMatch(/08:00|10:00/)
    expect(card.textContent).not.toContain('En cours')
    expect(screen.getByTestId('calendar-date-scroller').contains(card)).toBe(false)
  })

  it('keeps the date scroller as the day-grid owner when unplanned is expanded', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-timed',
              title: 'Brief cuisine',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [
            wrap({
              id: 'exec-unplanned-1',
              title: 'Sans créneau A',
              start_at: null,
              end_at: null,
            }),
            wrap({
              id: 'exec-unplanned-2',
              title: 'Sans créneau B',
              start_at: null,
              end_at: null,
            }),
          ],
        }}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Non planifiés' }))

    const hub = screen.getByTestId('calendar-hub-scroller')
    const timeScroller = screen.getByTestId('calendar-date-scroller')
    const unplannedList = screen.getByTestId('calendar-unplanned-list')
    expect(timeScroller.textContent).not.toContain('00:00')
    expect(screen.queryByText('Journée')).toBeNull()
    expect(screen.queryByTestId('calendar-all-day-lane')).toBeNull()
    expect(timeScroller.contains(screen.getByRole('button', { name: /Sans créneau A/ }))).toBe(false)
    expect(timeScroller.contains(unplannedList)).toBe(false)
    expect(collectOverflowYScrollElements(hub)).toEqual([timeScroller, unplannedList])
  })

  it('keeps week vertical overflow on the date scroller without a nested horizontal canvas', () => {
    render(
      <ExecutionCalendarView
        granularity="week"
        days={['2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13', '2026-09-14']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [],
          unplanned: [
            wrap({
              id: 'exec-unplanned',
              title: 'Sans créneau',
              start_at: null,
              end_at: null,
            }),
          ],
        }}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Non planifiés' }))

    const hub = screen.getByTestId('calendar-hub-scroller')
    const timeScroller = screen.getByTestId('calendar-date-scroller')
    expect(collectOverflowYScrollElements(hub)).toEqual([
      timeScroller,
      screen.getByTestId('calendar-unplanned-list'),
    ])
  })

  it('has no hourly grid or initial hour scroll in date-only views', () => {
    render(<ExecutionCalendarView granularity="day" days={['2026-09-08']} month="2026-09"
      isLoading={false} isError={false} error={null} onRetry={() => undefined}
      onOpenExecution={() => undefined} data={emptyCalendarData} />)
    expect(screen.queryByTestId('calendar-time-scroller')).toBeNull()
    expect(screen.queryByText('08:00')).toBeNull()
    expect(screen.getByTestId('calendar-date-scroller').scrollTop).toBe(0)
    expect(screen.getByText('Aucun plan sur cette période.')).toBeTruthy()
  })

  it('stacks all plans without hiding them behind a per-day overflow', () => {
    const onOpen = vi.fn()
    const items = Array.from({ length: 6 }, (_, i) => wrap({ id: `plan-${i}`, title: `Plan ${i}`, all_day: i % 2 === 0 }))
    render(<ExecutionCalendarView granularity="day" days={['2026-09-08']} month="2026-09"
      isLoading={false} isError={false} error={null} onRetry={() => undefined}
      onOpenExecution={onOpen} data={{ ...emptyCalendarData, items }} />)
    for (let i = 0; i < 6; i++) fireEvent.click(screen.getByRole('button', { name: new RegExp(`Plan ${i}`) }))
    expect(onOpen).toHaveBeenCalledTimes(6)
    expect(screen.queryByText(/de plus/)).toBeNull()
  })

  it('continues one execution across two month rows with the same target', () => {
    const onOpen = vi.fn()
    const item = wrap({ id: 'span', title: 'Chantier', start_at: combineCivilDateTimeToIso('2026-09-10', '14:00'), end_at: combineCivilDateTimeToIso('2026-09-15', '15:00') })
    render(<ExecutionCalendarView granularity="month" days={[...MONDAY_WEEK, '2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19', '2026-09-20']} month="2026-09"
      isLoading={false} isError={false} error={null} onRetry={() => undefined}
      onOpenExecution={onOpen} data={{ ...emptyCalendarData, items: [item] }} />)
    const spans = screen.getAllByTestId('calendar-span-span')
    expect(spans).toHaveLength(2)
    expect(spans[0].style.gridColumn).toBe('4 / 8')
    expect(spans[0].getAttribute('data-continues-after')).toBe('true')
    expect(spans[1].style.gridColumn).toBe('1 / 3')
    expect(spans[1].getAttribute('data-continues-before')).toBe('true')
    spans.forEach((button) => fireEvent.click(button))
    expect(onOpen.mock.calls).toEqual([['span'], ['span']])
  })

  it('shows a 3-day compact week window stepped by one day', () => {
    mockToday('2026-09-07')
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    expect(visibleWeekDays()).toEqual(['2026-09-07', '2026-09-08', '2026-09-09'])
    expect(screen.queryByTestId('calendar-weekday-2026-09-10')).toBeNull()
    expect(screen.getByTestId('calendar-date-scroller').textContent).not.toContain('00:00')
    expect(screen.getByRole('button', { name: 'Jours précédents de la semaine' })).toHaveProperty(
      'disabled',
      true,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Jours suivants de la semaine' }))

    expect(visibleWeekDays()).toEqual(['2026-09-08', '2026-09-09', '2026-09-10'])
    expect(screen.queryByTestId('calendar-weekday-2026-09-07')).toBeNull()
  })

  it('centers today in the compact week window when it is not at an edge', () => {
    mockToday('2026-09-10')
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    expect(visibleWeekDays()).toEqual(['2026-09-09', '2026-09-10', '2026-09-11'])
  })

  it('advances the compact week window by one day on a horizontal swipe', () => {
    mockToday('2026-09-07')
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    const card = screen.getByTestId('calendar-grid-card')
    fireEvent.pointerDown(card, { clientX: 200, clientY: 80 })
    fireEvent.pointerUp(card, { clientX: 140, clientY: 84 })

    expect(visibleWeekDays()).toEqual(['2026-09-08', '2026-09-09', '2026-09-10'])
  })

  it('pages the compact week from a chip swipe without opening the execution', () => {
    mockToday('2026-09-07')
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-swipe',
              title: 'Brief cuisine',
              start_at: combineCivilDateTimeToIso('2026-09-07', '08:00'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '09:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const chip = screen.getByRole('button', { name: /Brief cuisine/ })
    fireEvent.pointerDown(chip, { clientX: 200, clientY: 80 })
    fireEvent.pointerUp(chip, { clientX: 140, clientY: 84 })
    fireEvent.click(chip)

    expect(visibleWeekDays()).toEqual(['2026-09-08', '2026-09-09', '2026-09-10'])
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('opens the execution after a sub-threshold move without paging', () => {
    mockToday('2026-09-07')
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-tap',
              title: 'Brief cuisine',
              start_at: combineCivilDateTimeToIso('2026-09-07', '08:00'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '09:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const chip = screen.getByRole('button', { name: /Brief cuisine/ })
    fireEvent.pointerDown(chip, { clientX: 200, clientY: 80 })
    fireEvent.pointerUp(chip, { clientX: 180, clientY: 82 })
    fireEvent.click(chip)

    expect(visibleWeekDays()).toEqual(['2026-09-07', '2026-09-08', '2026-09-09'])
    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(onOpen).toHaveBeenCalledWith('exec-tap')
  })

  it('expires swipe click suppression so a later tap still opens', () => {
    mockToday('2026-09-07')
    vi.useFakeTimers()
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-later',
              title: 'Brief cuisine',
              start_at: combineCivilDateTimeToIso('2026-09-09', '08:00'),
              end_at: combineCivilDateTimeToIso('2026-09-09', '09:00'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    const card = screen.getByTestId('calendar-grid-card')
    fireEvent.pointerDown(card, { clientX: 200, clientY: 80 })
    fireEvent.pointerUp(card, { clientX: 140, clientY: 84 })

    expect(visibleWeekDays()).toEqual(['2026-09-08', '2026-09-09', '2026-09-10'])
    expect(onOpen).not.toHaveBeenCalled()

    vi.advanceTimersByTime(50)

    const chip = screen.getByRole('button', { name: /Brief cuisine/ })
    fireEvent.click(chip)

    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(onOpen).toHaveBeenCalledWith('exec-later')
  })

  it('keeps the compact 3-day week on a large touch screen', () => {
    installTestMatchMedia(true, 'coarse')
    mockToday('2026-09-10')
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    expect(visibleWeekDays()).toEqual(['2026-09-09', '2026-09-10', '2026-09-11'])
    expect(screen.getByTestId('calendar-week-next-days')).toBeTruthy()
    expect(screen.queryByTestId('calendar-desktop-week-grid')).toBeNull()
  })

  it('keeps one, two, and three overlapping plans independently clickable in the compact week', () => {
    mockToday('2026-09-07')
    const onOpen = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-solo',
              title: 'Seul',
              start_at: combineCivilDateTimeToIso('2026-09-07', '08:00'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '09:00'),
            }),
            wrap({
              id: 'exec-pair-a',
              title: 'Paire A',
              start_at: combineCivilDateTimeToIso('2026-09-07', '10:00'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '12:00'),
            }),
            wrap({
              id: 'exec-pair-b',
              title: 'Paire B',
              start_at: combineCivilDateTimeToIso('2026-09-07', '10:30'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '12:30'),
            }),
            wrap({
              id: 'exec-triple-a',
              title: 'Triple A',
              start_at: combineCivilDateTimeToIso('2026-09-07', '14:00'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '16:00'),
            }),
            wrap({
              id: 'exec-triple-b',
              title: 'Triple B',
              start_at: combineCivilDateTimeToIso('2026-09-07', '14:15'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '16:15'),
            }),
            wrap({
              id: 'exec-triple-c',
              title: 'Triple C',
              start_at: combineCivilDateTimeToIso('2026-09-07', '14:30'),
              end_at: combineCivilDateTimeToIso('2026-09-07', '16:30'),
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    for (const title of ['Seul', 'Paire A', 'Paire B', 'Triple A', 'Triple B', 'Triple C']) {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(title) }))
    }
    expect(onOpen).toHaveBeenCalledTimes(6)
    expect(onOpen).toHaveBeenCalledWith('exec-solo')
    expect(onOpen).toHaveBeenCalledWith('exec-pair-b')
    expect(onOpen).toHaveBeenCalledWith('exec-triple-c')
  })

  it('keeps the first calendar load as a full replacement without a date scroller', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )

    expect(screen.getByText('Chargement du calendrier…')).toBeTruthy()
    expect(screen.queryByTestId('calendar-date-scroller')).toBeNull()
    expect(screen.queryByTestId('calendar-period-pending')).toBeNull()
  })

  it('keeps the selected-period chrome while waiting for an uncached window', () => {
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-day',
              title: 'Brief cuisine',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()

    rerender(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-09']}
        month="2026-09"
        isLoading
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )

    expect(screen.getByTestId('calendar-weekday-2026-09-09')).toBeTruthy()
    expect(screen.queryByTestId('calendar-weekday-2026-09-08')).toBeNull()
    expect(screen.getByTestId('calendar-date-scroller')).toBeTruthy()
    expect(screen.getByTestId('calendar-period-pending')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Brief cuisine/ })).toBeNull()
    expect(screen.queryByText('Chargement du calendrier…')).toBeNull()
  })

  it('does not treat a day payload as a settled empty week while the week key is pending', () => {
    stubMatchMedia(true)
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-day',
              title: 'Brief cuisine',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    rerender(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )

    expect(screen.getByTestId('calendar-weekday-2026-09-07')).toBeTruthy()
    expect(screen.queryByTestId('calendar-weekday-2026-09-13')).toBeNull()
    expect(screen.queryByRole('button', { name: /Brief cuisine/ })).toBeNull()
    expect(screen.getByTestId('calendar-period-pending')).toBeTruthy()
  })

  it('hides the period-pending status once the current key succeeds with an empty window', () => {
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    rerender(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-09']}
        month="2026-09"
        isLoading
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )
    expect(screen.getByTestId('calendar-period-pending')).toBeTruthy()

    rerender(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-09']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    expect(screen.queryByTestId('calendar-period-pending')).toBeNull()
    expect(screen.getByTestId('calendar-date-scroller')).toBeTruthy()
  })

  it('does not show period pending when the current key already has data', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-day',
              title: 'Brief cuisine',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()
    expect(screen.queryByTestId('calendar-period-pending')).toBeNull()
  })

  it('keeps the selected chrome and retry when a later period fetch fails', () => {
    const onRetry = vi.fn()
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={onRetry}
        onOpenExecution={() => undefined}
        data={{
          timezone: 'Europe/Paris',
          items: [
            wrap({
              id: 'exec-day',
              title: 'Brief cuisine',
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        }}
      />,
    )

    rerender(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-09']}
        month="2026-09"
        isLoading={false}
        isError
        error={new ActionPlansApiError({ status: 500, detail: 'Impossible de charger le calendrier.' })}
        onRetry={onRetry}
        onOpenExecution={() => undefined}
      />,
    )

    expect(screen.getByTestId('calendar-weekday-2026-09-09')).toBeTruthy()
    expect(screen.getByTestId('calendar-date-scroller')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Brief cuisine/ })).toBeNull()
    expect(screen.getByTestId('calendar-period-error')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('keeps the first error as a full replacement before any calendar chrome', () => {
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        isLoading={false}
        isError
        error={new ActionPlansApiError({ status: 500, detail: 'Impossible de charger le calendrier.' })}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )

    expect(screen.getByText('Impossible de charger le calendrier.')).toBeTruthy()
    expect(screen.queryByTestId('calendar-date-scroller')).toBeNull()
    expect(screen.queryByTestId('calendar-period-error')).toBeNull()
  })

  it('resolves today from the provided calendar timezone', () => {
    const spy = vi.spyOn(businessTimezone, 'todayCivilDate')
    render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-08']}
        month="2026-09"
        timeZone="UTC"
        isLoading
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
      />,
    )
    expect(spy).toHaveBeenCalledWith('UTC')
  })

  it('tints desktop date headers without changing execution or outside-month surfaces', () => {
    installTestMatchMedia(true, 'fine')
    mockToday('2026-09-10')
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-09-10']}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )
    const dayHeader = screen.getByTestId('calendar-weekday-2026-09-10')
    expect(dayHeader.className).toContain('bg-[#FAFAF8]')
    expect(dayHeader.className).toContain('px-1')
    expect(dayHeader.className).toContain('py-2')
    const dayPill = dayHeader.querySelector('.rounded-full')
    expect(dayPill?.className).toContain('h-7')
    expect(dayPill?.className).toContain('bg-[#114660]')
    expect(screen.getByText('Aucune exécution').className).not.toContain('bg-[#FAFAF8]')

    rerender(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'week-span',
              title: 'Chantier',
              start_at: combineCivilDateTimeToIso('2026-09-08', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-09-10', '18:00'),
            }),
          ],
        }}
      />,
    )
    for (const day of MONDAY_WEEK) {
      const header = screen.getByTestId(`calendar-weekday-${day}`)
      expect(header.className).toContain('bg-[#FAFAF8]')
      expect(header.className).toContain('border-b')
      expect(screen.getByTestId(`calendar-desktop-column-${day}`).className).not.toContain('bg-[#FAFAF8]')
    }
    expect(screen.getByTestId('calendar-weekday-2026-09-10').querySelector('.rounded-full')?.className).toContain('bg-[#114660]')
    expect(screen.getByTestId('calendar-bands').className).toContain('bg-white')

    const monthWindow = resolveCalendarWindow('month', '2026-09-15')
    rerender(
      <ExecutionCalendarView
        granularity="month"
        days={monthWindow.days}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'month-single',
              title: 'Brief',
              start_at: combineCivilDateTimeToIso('2026-09-15', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-09-15', '10:00'),
            }),
            wrap({
              id: 'month-outside',
              title: 'Dehors',
              start_at: combineCivilDateTimeToIso('2026-08-31', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '10:00'),
            }),
          ],
        }}
      />,
    )
    const inMonthHeader = screen.getByTestId('calendar-weekday-2026-09-15')
    expect(inMonthHeader.className).toContain('bg-[#FAFAF8]')
    expect(inMonthHeader.className).not.toContain('bg-[#F5F4F0]')
    expect(inMonthHeader.querySelector('.rounded-full')?.className).not.toContain('bg-[#114660]')
    const outsideHeader = screen.getByTestId('calendar-weekday-2026-08-31')
    expect(outsideHeader.className).toContain('bg-[#F5F4F0]')
    expect(outsideHeader.className).not.toContain('bg-[#FAFAF8]')
    const executionCell = screen.getByTestId('calendar-event-month-single').parentElement
    expect(executionCell?.className).not.toContain('bg-[#FAFAF8]')
    expect(executionCell?.className).not.toContain('bg-[#F5F4F0]')
    const outsideCell = screen.getByTestId('calendar-event-month-outside').parentElement
    expect(outsideCell?.className).toContain('bg-[#F5F4F0]')
    expect(outsideCell?.className).not.toContain('bg-[#FAFAF8]')
  })

  it('shows an empty desktop day and a mixed day in group order', () => {
    installTestMatchMedia(false, 'fine')
    const { rerender } = render(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-10-13']}
        month="2026-10"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )
    expect(screen.getByText('Aucune exécution')).toBeTruthy()
    expect(screen.queryByTestId('calendar-desktop-day-count')).toBeNull()

    rerender(
      <ExecutionCalendarView
        granularity="day"
        days={['2026-10-13']}
        month="2026-10"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'timed',
              title: 'Brief planifié',
              status: 'scheduled',
              start_at: combineCivilDateTimeToIso('2026-10-13', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-10-13', '10:00'),
              involved_poles: [{ business_unit: { specific_name: 'Cuisine' } }],
            }),
            wrap({
              id: 'all',
              title: 'Inventaire',
              all_day: true,
              start_at: combineCivilDateTimeToIso('2026-10-13', '00:00'),
              end_at: combineCivilDateTimeToIso('2026-10-13', '23:59'),
            }),
            wrap({
              id: 'multi',
              title: 'Chantier',
              status: 'pending_validation',
              start_at: combineCivilDateTimeToIso('2026-10-12', '18:00'),
              end_at: combineCivilDateTimeToIso('2026-10-14', '09:00'),
            }),
          ],
        }}
      />,
    )

    const headings = screen.getAllByRole('heading').map((heading) => heading.textContent)
    expect(headings).toEqual(['Multi-jours', 'Journée entière', 'Dans la journée'])
    expect(screen.getByTestId('calendar-desktop-day-count').textContent).toBe('3 exécutions')
    const timed = screen.getByRole('button', { name: /Brief planifié/ })
    expect(timed.textContent).toContain('Planifié')
    expect(timed.textContent).toContain('Restaurant')
    expect(timed.textContent).not.toContain('Cuisine')
    expect(timed.textContent).toContain('09:00')
    expect(screen.getByRole('button', { name: /Chantier/ }).textContent).toContain('À valider')
    expect(screen.queryByText(/\+\d+ autre/)).toBeNull()
  })

  it('keeps seven readable desktop week columns on a narrow computer window', () => {
    installTestMatchMedia(false, 'fine')
    mockToday('2026-09-10')
    const items = Array.from({ length: 6 }, (_, index) =>
      wrap({
        id: `plan-${index}`,
        title: `Plan ${index}`,
        start_at: combineCivilDateTimeToIso('2026-09-08', '09:00'),
        end_at: combineCivilDateTimeToIso('2026-09-08', '10:00'),
        assignees:
          index === 0 ? [{ membership_id: 'm-1', display_name: 'Alice Martin' }] : [],
        establishment_name: index === 0 ? 'Hôtel du Parc' : undefined,
      }),
    )
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        showEstablishment
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{ ...emptyCalendarData, items }}
      />,
    )

    const grid = screen.getByTestId('calendar-desktop-week-grid')
    expect(grid.style.gridTemplateColumns).toBe('repeat(7, minmax(11rem, 1fr))')
    expect(grid.style.minWidth).toBe('77rem')
    expect(screen.getByTestId('calendar-desktop-week-scroller').className).toContain('overflow-auto')
    expect(visibleWeekDays()).toEqual([...MONDAY_WEEK])
    expect(screen.queryByTestId('calendar-week-next-days')).toBeNull()
    expect(screen.queryByText(/\+\d+ autre/)).toBeNull()
    expect(screen.getAllByRole('button', { name: /Plan / })).toHaveLength(6)
    const line = screen.getByTestId('calendar-event-plan-0')
    expect(line.className).toContain('items-start')
    expect(line.className).toContain('py-1')
    expect(line.className).not.toContain('py-1.5')
    const title = line.querySelector('span.font-semibold')
    expect(title?.textContent).toBe('Plan 0')
    expect(title?.className).toContain('text-xs')
    expect(title?.className).toContain('line-clamp-2')
    expect(title?.className).not.toContain('text-sm')
    expect(title?.className).not.toContain('truncate')
    expect(line.getAttribute('title')).toBe('Plan 0')
    const meta = line.querySelector('span.tabular-nums')?.parentElement
    expect(meta?.className).toContain('text-[11px]')
    expect(meta?.className).toContain('text-[#7D7B75]')
    expect(line.textContent).toContain('09:00')
    expect(line.textContent).toContain('Restaurant')
    expect(line.textContent).toContain('Hôtel du Parc')
    expect(line.textContent).not.toContain('Alice Martin')
    expect(line.getAttribute('aria-label')).toContain('Alice Martin')
    expect(screen.queryByTestId('calendar-status-pill-plan-0')).toBeNull()
    expect(screen.getByTestId('calendar-desktop-column-2026-09-08').className).toContain('divide-y')
    const dot = screen.getByTestId('calendar-status-dot-plan-0')
    expect(dot.className).toContain('rounded-full')
    expect(dot.style.backgroundColor).toBe('rgb(58, 122, 150)')
  })

  it('opens the desktop day of an outside-month date from the overflow control', () => {
    installTestMatchMedia(true, 'fine')
    const onOpenDay = vi.fn()
    const onOpen = vi.fn()
    const monthWindow = resolveCalendarWindow('month', '2026-09-15')
    const outsideDay = monthWindow.days.find((day) => !day.startsWith('2026-09'))
    expect(outsideDay).toBe('2026-08-31')
    render(
      <ExecutionCalendarView
        granularity="month"
        days={monthWindow.days}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={onOpen}
        onOpenDay={onOpenDay}
        showEstablishment
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'out-1',
              title: 'Dehors 1',
              establishment_name: 'Hôtel du Parc',
              start_at: combineCivilDateTimeToIso('2026-08-31', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '10:00'),
            }),
            wrap({
              id: 'out-2',
              title: 'Dehors 2',
              establishment_name: 'Hôtel du Parc',
              start_at: combineCivilDateTimeToIso('2026-08-31', '11:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '12:00'),
            }),
            wrap({
              id: 'out-3',
              title: 'Dehors 3',
              establishment_name: 'Hôtel du Parc',
              start_at: combineCivilDateTimeToIso('2026-08-31', '13:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '14:00'),
            }),
          ],
        }}
      />,
    )

    const outside = screen.getByRole('button', { name: /Dehors 1/ })
    expect(outside.textContent).toContain('Hôtel du Parc')
    expect(outside.textContent).not.toContain('En cours')
    expect(screen.getByTestId('calendar-status-dot-out-1').getAttribute('style')).toContain('background-color')
    expect(screen.getByTestId('calendar-establishment-out-1').className).not.toContain('sr-only')
    expect(screen.queryByRole('button', { name: /Dehors 3/ })).toBeNull()
    fireEvent.click(screen.getByTestId('calendar-month-overflow-2026-08-31'))
    expect(onOpenDay).toHaveBeenCalledWith('2026-08-31')
    expect(onOpen).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Dehors 1/ }))
    expect(onOpen).toHaveBeenCalledWith('out-1')
  })

  it('collapses desktop month weeks that have no executions', () => {
    installTestMatchMedia(true, 'fine')
    const monthWindow = resolveCalendarWindow('month', '2026-09-15')
    const onOpenDay = vi.fn()
    render(
      <ExecutionCalendarView
        granularity="month"
        days={monthWindow.days}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        onOpenDay={onOpenDay}
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'out-1',
              title: 'Dehors 1',
              start_at: combineCivilDateTimeToIso('2026-08-31', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '10:00'),
            }),
            wrap({
              id: 'out-2',
              title: 'Dehors 2',
              start_at: combineCivilDateTimeToIso('2026-08-31', '11:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '12:00'),
            }),
            wrap({
              id: 'out-3',
              title: 'Dehors 3',
              start_at: combineCivilDateTimeToIso('2026-08-31', '13:00'),
              end_at: combineCivilDateTimeToIso('2026-08-31', '14:00'),
            }),
            wrap({
              id: 'span',
              title: 'Chantier',
              start_at: combineCivilDateTimeToIso('2026-09-08', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-09-10', '18:00'),
            }),
            wrap({
              id: 'single',
              title: 'Brief',
              start_at: combineCivilDateTimeToIso('2026-09-15', '09:00'),
              end_at: combineCivilDateTimeToIso('2026-09-15', '10:00'),
            }),
          ],
        }}
      />,
    )

    for (const day of monthWindow.days) {
      expect(screen.getByTestId(`calendar-weekday-${day}`)).toBeTruthy()
    }

    const outsideWeek = screen.getByTestId('calendar-desktop-month-week-2026-08-31')
    expect(outsideWeek.getAttribute('data-empty')).toBe('false')
    expect(outsideWeek.querySelector('[data-testid="calendar-desktop-month-days"]')).toBeTruthy()
    expect(screen.getByTestId('calendar-weekday-2026-08-31').className).toContain('bg-[#F5F4F0]')
    fireEvent.click(screen.getByTestId('calendar-month-overflow-2026-08-31'))
    expect(onOpenDay).toHaveBeenCalledWith('2026-08-31')

    const bandWeek = screen.getByTestId('calendar-desktop-month-week-2026-09-07')
    expect(bandWeek.getAttribute('data-empty')).toBe('false')
    expect(bandWeek.querySelector('[data-testid="calendar-span-span"]')).toBeTruthy()
    expect(bandWeek.querySelector('[data-testid="calendar-desktop-month-days"]')).toBeNull()
    expect(bandWeek.className).not.toContain('flex-1')
    expect(bandWeek.className).not.toContain('min-h-')

    const busyWeek = screen.getByTestId('calendar-desktop-month-week-2026-09-14')
    expect(busyWeek.getAttribute('data-empty')).toBe('false')
    expect(busyWeek.querySelector('[data-testid="calendar-event-single"]')).toBeTruthy()
    expect(busyWeek.querySelector('[data-testid="calendar-desktop-month-days"]')).toBeTruthy()
    expect(busyWeek.className).not.toContain('flex-1')
    expect(busyWeek.className).not.toContain('min-h-')

    for (const start of ['2026-09-21', '2026-09-28']) {
      const emptyWeek = screen.getByTestId(`calendar-desktop-month-week-${start}`)
      expect(emptyWeek.getAttribute('data-empty')).toBe('true')
      expect(emptyWeek.querySelector('[data-testid="calendar-desktop-month-days"]')).toBeNull()
      expect(emptyWeek.querySelector('[data-testid="calendar-bands"]')).toBeNull()
      expect(emptyWeek.className).not.toContain('flex-1')
      expect(emptyWeek.className).not.toContain('min-h-')
    }
    expect(screen.getByTestId('calendar-weekday-2026-10-04').className).toContain('bg-[#F5F4F0]')
    expect(screen.queryByTestId('calendar-desktop-month-empty')).toBeNull()
  })

  it('shows one discreet message when the desktop month has no executions', () => {
    installTestMatchMedia(true, 'fine')
    const monthWindow = resolveCalendarWindow('month', '2026-09-15')
    render(
      <ExecutionCalendarView
        granularity="month"
        days={monthWindow.days}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    const message = screen.getByTestId('calendar-desktop-month-empty')
    expect(message.textContent).toBe('Aucun plan sur cette période.')
    expect(message.className).toContain('text-xs')
    expect(message.className).not.toContain('py-6')
    expect(screen.getAllByText('Aucun plan sur cette période.')).toHaveLength(1)
    const weekStarts = monthWindow.days.filter((_, index) => index % 7 === 0)
    expect(weekStarts.length).toBeGreaterThan(1)
    for (const start of weekStarts) {
      const week = screen.getByTestId(`calendar-desktop-month-week-${start}`)
      expect(week.getAttribute('data-empty')).toBe('true')
      expect(week.querySelector('[data-testid="calendar-desktop-month-days"]')).toBeNull()
      expect(week.querySelectorAll('[data-testid^="calendar-weekday-"]')).toHaveLength(7)
    }
    expect(screen.getByTestId('calendar-weekday-2026-08-31').className).toContain('bg-[#F5F4F0]')
  })

  it('shows the establishment on a mobile cross month band', () => {
    render(
      <ExecutionCalendarView
        granularity="month"
        days={['2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13']}
        month="2026-09"
        showEstablishment
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={{
          ...emptyCalendarData,
          items: [
            wrap({
              id: 'exec-cross',
              title: 'Brief cuisine',
              establishment_name: 'Hôtel du Parc',
              involved_poles: [{ business_unit: { specific_name: 'Cuisine' } }],
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
        }}
      />,
    )

    const establishment = screen.getByTestId('calendar-establishment-exec-cross')
    expect(establishment.textContent).toBe('Hôtel du Parc')
    expect(establishment.className).not.toContain('sr-only')
    const chip = screen.getByRole('button', { name: /Brief cuisine/ })
    expect(chip.textContent).toContain('Restaurant')
    expect(chip.textContent).not.toContain('Cuisine')
  })

  it('keeps the compact week in the native runtime even with a fine pointer', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    installTestMatchMedia(true, 'fine')
    mockToday('2026-09-10')
    render(
      <ExecutionCalendarView
        granularity="week"
        days={[...MONDAY_WEEK]}
        month="2026-09"
        isLoading={false}
        isError={false}
        error={null}
        onRetry={() => undefined}
        onOpenExecution={() => undefined}
        data={emptyCalendarData}
      />,
    )

    expect(screen.queryByTestId('calendar-desktop-week-grid')).toBeNull()
    expect(visibleWeekDays()).toEqual(['2026-09-09', '2026-09-10', '2026-09-11'])
  })
})



it('proposes a deadline change on desktop drop, without navigating or mutating a plan', () => {
  vi.stubEnv('VITE_APP_RUNTIME', 'web')
  installTestMatchMedia(true, 'fine')
  const drop = vi.fn()
  const open = vi.fn()
  const item = wrap({ id: 'drag-plan', title: 'Podium' })
  item.action_plan_execution.permission_hints.can_update = true
  render(<ExecutionCalendarView granularity="week" days={[...MONDAY_WEEK]} month="2026-09"
    data={{ ...emptyCalendarData, items: [item] }} isLoading={false} isError={false} error={null}
    onRetry={vi.fn()} onOpenExecution={open} onDeadlineDrop={drop} />)
  const card = screen.getByTestId('calendar-event-drag-plan')
  expect(card.getAttribute('draggable')).toBe('true')
  fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn(), effectAllowed: '' } })
  fireEvent.dragOver(screen.getByTestId('calendar-weekday-2026-09-10'))
  fireEvent.drop(screen.getByTestId('calendar-weekday-2026-09-10'))
  expect(drop).toHaveBeenCalledWith('drag-plan', '2026-09-10')
  expect(open).not.toHaveBeenCalled()
})
