// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItemWrapper } from '@/features/action-plans/types'

import { ExecutionUpcomingPage } from './execution-upcoming-page'

const upcomingQueryMock = vi.fn()
const onOpenActionPlanExecution = vi.fn()
const pinControl = vi.hoisted(() => {
  const control = {
    failPin: false,
    pin: vi.fn(
      (
        _id: string,
        options?: { onSuccess?: () => void; onError?: (error: unknown) => void },
      ) => {
        if (control.failPin) {
          options?.onError?.(new Error('Épinglage impossible.'))
          return
        }
        options?.onSuccess?.()
      },
    ),
    unpin: vi.fn(
      (
        _id: string,
        options?: { onSuccess?: () => void; onError?: (error: unknown) => void },
      ) => {
        options?.onSuccess?.()
      },
    ),
  }
  return control
})

function buildUpcomingWrapper(
  id: string,
  title: string,
  overrides: Partial<ActionPlanExecutionFeedItemWrapper['action_plan_execution']> = {},
): ActionPlanExecutionFeedItemWrapper {
  return {
    item_type: 'action_plan_execution',
    action_plan_execution: {
      id,
      title,
      description_short: 'Description plan',
      status: 'scheduled',
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
      assignees: [{ membership_id: 'member-1', display_name: 'Alice' }],
      start_at: '2026-07-13T12:00:00Z',
      end_at: '2026-07-13T16:00:00Z',
      all_day: false,
      is_overdue: false,
      task_count: 4,
      treated_task_count: 1,
      task_executions: [],
      last_activity_at: '2026-06-13T12:00:00Z',
      created_at: '2026-06-13T12:00:00Z',
      created_by_display_name: 'Alice Martin',
      is_pinned: false,
      permission_hints: {
        can_mark_done: false,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_update: false,
        is_pilot_pole_assignee: false,
        can_pin: true,
      },
      ...overrides,
    },
  }
}

function buildUpcomingQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    refetch: vi.fn(),
    data: {
      pages: [
        {
          items: [buildUpcomingWrapper('plan-scheduled', 'Plan programmé')],
          next_cursor: null,
          has_more: false,
        },
      ],
    },
    ...overrides,
  }
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        establishment_id: 'est-1',
        role: 'staff',
      },
    },
  }),
}))

vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionUpcomingQuery: () => upcomingQueryMock(),
  usePinActionPlanExecutionMutation: () => ({
    mutate: pinControl.pin,
    isPending: false,
  }),
  useUnpinActionPlanExecutionMutation: () => ({
    mutate: pinControl.unpin,
    isPending: false,
  }),
}))

function stubLgViewport(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
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

function renderUpcomingPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ExecutionUpcomingPage, { onOpenActionPlanExecution }),
    ),
  )
}

describe('ExecutionUpcomingPage', () => {
  beforeEach(() => {
    onOpenActionPlanExecution.mockClear()
    upcomingQueryMock.mockReturnValue(buildUpcomingQueryState())
    pinControl.failPin = false
    pinControl.pin.mockClear()
    pinControl.unpin.mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('renders the desktop row with the start date on web lg', () => {
    stubLgViewport(true)
    upcomingQueryMock.mockReturnValue(
      buildUpcomingQueryState({
        data: {
          pages: [
            {
              items: [
                buildUpcomingWrapper('plan-all-day', 'Brief journée', {
                  all_day: true,
                  start_at: '2026-07-13T00:00:00Z',
                }),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )
    renderUpcomingPage()

    const openControl = screen.getByRole('button', { name: /Brief journée/ })
    const actions = screen.getByRole('button', { name: 'Actions du plan d’action' })
    expect(openControl.contains(actions)).toBe(false)
    expect(screen.getByText(/^Début : /)).toBeTruthy()
    expect(screen.queryByText(/Journée entière/)).toBeNull()
    expect(screen.queryByText('DÉBUT')).toBeNull()
    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.getByText('Alice Martin')).toBeTruthy()

    fireEvent.click(actions)
    expect(onOpenActionPlanExecution).not.toHaveBeenCalled()
    expect(screen.getByRole('menu', { name: 'Actions du plan d’action' })).toBeTruthy()
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()

    fireEvent.click(openControl)
    expect(onOpenActionPlanExecution).toHaveBeenCalledWith('plan-all-day')
  })

  it('closes the desktop pin menu after a successful pin of the opened row', async () => {
    stubLgViewport(true)
    renderUpcomingPage()

    fireEvent.click(screen.getByRole('button', { name: 'Actions du plan d’action' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    expect(pinControl.pin).toHaveBeenCalledWith('plan-scheduled', expect.any(Object))
    await waitFor(() => {
      expect(screen.queryByRole('menu', { name: 'Actions du plan d’action' })).toBeNull()
    })
  })

  it('keeps the desktop pin menu open with the error, then clears it on another row', () => {
    stubLgViewport(true)
    pinControl.failPin = true
    upcomingQueryMock.mockReturnValue(
      buildUpcomingQueryState({
        data: {
          pages: [
            {
              items: [
                buildUpcomingWrapper('plan-scheduled', 'Plan programmé'),
                buildUpcomingWrapper('plan-other', 'Plan autre'),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )
    renderUpcomingPage()

    const [firstActions, secondActions] = screen.getAllByRole('button', {
      name: 'Actions du plan d’action',
    })
    fireEvent.click(firstActions)
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    expect(screen.getByRole('alert').textContent).toBe('Épinglage impossible.')
    expect(screen.getByRole('menu', { name: 'Actions du plan d’action' })).toBeTruthy()

    fireEvent.click(secondActions)
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByRole('menu', { name: 'Actions du plan d’action' })).toBeTruthy()
  })

  it('keeps the scheduled card and the actions sheet outside desktop web', () => {
    stubLgViewport(false)
    renderUpcomingPage()

    const openControl = screen.getByRole('button', { name: /Plan programmé/ })
    const actions = screen.getByRole('button', { name: 'Actions du plan d’action' })
    expect(openControl.contains(actions)).toBe(true)
    expect(screen.getByText('DÉBUT')).toBeTruthy()
    expect(screen.queryByText(/^Début : /)).toBeNull()

    fireEvent.click(actions)
    expect(onOpenActionPlanExecution).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog', { name: 'Actions' })).toBeTruthy()
    expect(screen.queryByRole('menu', { name: 'Actions du plan d’action' })).toBeNull()
  })

  it('keeps the scheduled card on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    renderUpcomingPage()

    const openControl = screen.getByRole('button', { name: /Plan programmé/ })
    const actions = screen.getByRole('button', { name: 'Actions du plan d’action' })
    expect(openControl.contains(actions)).toBe(true)
    expect(screen.getByText('DÉBUT')).toBeTruthy()
    fireEvent.click(actions)
    expect(screen.getByRole('dialog', { name: 'Actions' })).toBeTruthy()
    expect(screen.queryByRole('menu', { name: 'Actions du plan d’action' })).toBeNull()
  })
})
