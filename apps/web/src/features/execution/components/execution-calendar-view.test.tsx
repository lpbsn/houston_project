// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { combineCivilDateTimeToIso } from '@/lib/business-timezone'
import { collectOverflowYScrollElements } from '@/lib/terrain-scroll-layout'

import { ExecutionCalendarView } from './execution-calendar-view'

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

const TIME_GRID_INITIAL_SCROLL_TOP = 8 * 48

const emptyCalendarData = {
  timezone: 'Europe/Paris' as const,
  items: [] as ReturnType<typeof wrap>[],
  unplanned: [] as ReturnType<typeof wrap>[],
}

afterEach(() => {
  cleanup()
})

describe('ExecutionCalendarView', () => {
  it('keeps overlapping timed events independently clickable', () => {
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

  it('keeps unplanned collapsed and places 00:00 in the dedicated time scroller', () => {
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

    const hub = screen.getByTestId('calendar-hub-scroller')
    const gridCard = screen.getByTestId('calendar-grid-card')
    expect(hub.className).not.toMatch(/overflow-y-auto/)
    expect(hub.className).toMatch(/overflow-hidden/)
    expect(gridCard.className).toMatch(/min-h-0/)
    expect(gridCard.className).toMatch(/flex-1/)
    expect(gridCard.className).not.toMatch(/min-h-full/)
    expect(
      gridCard.compareDocumentPosition(unplannedToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()

    const scroller = screen.getByTestId('calendar-time-scroller')
    expect(scroller.className).toMatch(/overflow-y-auto/)
    expect(scroller.scrollTop).toBe(TIME_GRID_INITIAL_SCROLL_TOP)
    expect(scroller.textContent).toContain('00:00')
    expect(scroller.contains(screen.getByText('Journée'))).toBe(false)
    expect(screen.getByText('Journée').compareDocumentPosition(scroller) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brief cuisine/ }).textContent).toContain('En cours')
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

  it('renders scheduled and pending_validation timed events on the day grid', () => {
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
    expect(scheduled.textContent).toContain('Planifiée')
    expect(scheduled.querySelector('svg')).toBeNull()
    expect(pending.textContent).toContain('Validation')
    expect(pending.querySelector('svg')).toBeTruthy()
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
    expect(chip.textContent).toContain('En cours')
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
    expect(scroller.className).toMatch(/overflow-y-auto/)
    expect(scroller.contains(grid)).toBe(true)
    expect(scroller.contains(unplannedToggle)).toBe(false)
    expect(grid.className).not.toMatch(/overflow-y-auto/)
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
    expect(screen.getByTestId('calendar-unplanned-list').className).toMatch(/overflow-y-auto/)
    expect(collectOverflowYScrollElements(scroller)).toEqual([])
  })

  it('opens the same execution from a timed grid block and a day-lane continuation', () => {
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
    expect(chips.some((chip) => chip.textContent?.includes('Suite'))).toBe(true)
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
    expect(screen.getByTestId('calendar-time-scroller').contains(chip)).toBe(false)
  })

  it('keeps a full-day timed span on month cells without using the day-lane projection', () => {
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

    expect(screen.getAllByRole('button', { name: /Chantier toiture/ }).length).toBeGreaterThan(1)
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
    expect(screen.getByTestId('calendar-time-scroller').contains(card)).toBe(false)
    expect(screen.getByTestId('calendar-unplanned-list').className).toMatch(/overflow-y-auto/)
  })

  it('keeps the time scroller as the day-grid owner when unplanned is expanded', () => {
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
    const gridCard = screen.getByTestId('calendar-grid-card')
    const timeScroller = screen.getByTestId('calendar-time-scroller')
    const unplannedList = screen.getByTestId('calendar-unplanned-list')
    const innerColumn = timeScroller.parentElement
    expect(hub.className).not.toMatch(/overflow-y-auto/)
    expect(hub.className).toMatch(/overflow-hidden/)
    expect(gridCard.className).toMatch(/min-h-0/)
    expect(gridCard.className).toMatch(/\bflex-1\b/)
    expect(gridCard.className).not.toMatch(/min-h-full/)
    expect(innerColumn?.className).toMatch(/min-h-0/)
    expect(innerColumn?.className).toMatch(/\bflex-1\b/)
    expect(timeScroller.className).toMatch(/overflow-y-auto/)
    expect(timeScroller.className).toMatch(/overscroll-y-contain/)
    expect(timeScroller.className).toMatch(/min-h-0/)
    expect(timeScroller.className).toMatch(/\bflex-1\b/)
    expect(timeScroller.textContent).toContain('00:00')
    expect(timeScroller.contains(screen.getByText('Journée'))).toBe(false)
    expect(timeScroller.contains(screen.getByRole('button', { name: /Sans créneau A/ }))).toBe(false)
    expect(unplannedList.className).toMatch(/overflow-y-auto/)
    expect(timeScroller.contains(unplannedList)).toBe(false)
    expect(collectOverflowYScrollElements(hub)).toEqual([timeScroller, unplannedList])
  })

  it('keeps week horizontal overflow on the card without a nested vertical scroller when unplanned is expanded', () => {
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
    const gridCard = screen.getByTestId('calendar-grid-card')
    const timeScroller = screen.getByTestId('calendar-time-scroller')
    expect(hub.className).not.toMatch(/overflow-y-auto/)
    expect(gridCard.className).toMatch(/overflow-x-auto/)
    expect(gridCard.className).toMatch(/overflow-y-hidden/)
    expect(gridCard.className).not.toMatch(/overflow-y-auto/)
    expect(timeScroller.className).toMatch(/overflow-y-auto/)
    expect(collectOverflowYScrollElements(hub)).toEqual([
      timeScroller,
      screen.getByTestId('calendar-unplanned-list'),
    ])
  })

  it('aligns the time grid to 08:00 only when first entering the day or week grid', () => {
    const viewProps = {
      month: '2026-09',
      isError: false,
      error: null,
      onRetry: () => undefined,
      onOpenExecution: () => undefined,
      data: emptyCalendarData,
    }
    const { rerender } = render(
      <ExecutionCalendarView granularity="day" days={['2026-09-08']} isLoading={false} {...viewProps} />,
    )

    const firstScroller = screen.getByTestId('calendar-time-scroller')
    expect(firstScroller.scrollTop).toBe(TIME_GRID_INITIAL_SCROLL_TOP)

    firstScroller.scrollTop = 100
    rerender(
      <ExecutionCalendarView granularity="day" days={['2026-09-09']} isLoading={false} {...viewProps} />,
    )
    expect(screen.getByTestId('calendar-time-scroller').scrollTop).toBe(100)

    rerender(
      <ExecutionCalendarView granularity="week" days={['2026-09-08', '2026-09-09']} isLoading={false} {...viewProps} />,
    )
    expect(screen.getByTestId('calendar-time-scroller').scrollTop).toBe(100)

    rerender(
      <ExecutionCalendarView granularity="day" days={['2026-09-10']} isLoading {...viewProps} />,
    )
    expect(screen.queryByTestId('calendar-time-scroller')).toBeNull()

    rerender(
      <ExecutionCalendarView granularity="day" days={['2026-09-10']} isLoading={false} {...viewProps} />,
    )
    expect(screen.getByTestId('calendar-time-scroller').scrollTop).toBe(0)

    rerender(
      <ExecutionCalendarView
        granularity="month"
        days={['2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13']}
        isLoading={false}
        {...viewProps}
      />,
    )
    rerender(
      <ExecutionCalendarView granularity="day" days={['2026-09-11']} isLoading={false} {...viewProps} />,
    )
    expect(screen.getByTestId('calendar-time-scroller').scrollTop).toBe(TIME_GRID_INITIAL_SCROLL_TOP)
  })
})

