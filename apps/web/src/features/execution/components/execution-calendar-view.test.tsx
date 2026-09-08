// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

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
    expect(screen.queryByText('Sans créneau')).toBeNull()

    const scroller = screen.getByTestId('calendar-time-scroller')
    expect(scroller.textContent).toContain('00:00')
    expect(scroller.contains(screen.getByText('Journée'))).toBe(false)
    expect(screen.getByText('Journée').compareDocumentPosition(scroller) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brief cuisine/ }).textContent).toContain('En cours')
  })
})
