// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItemWrapper } from '@/features/action-plans/types'

import { ExecutionUpcomingPage } from './execution-upcoming-page'

const upcomingQueryMock = vi.fn()
const upcomingQueryArgs = vi.fn()
const upcomingNavigate = vi.fn()
const upcomingRouteState = { search: '' }
let serializeAppRouteMockPath = '/execution/upcoming'
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
      visible_from: null,
      marked_done_at: null,
      canceled_at: null,
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
  useActionPlanExecutionUpcomingQuery: (
    establishmentId: string | null,
    viewMode: string,
    options?: { source?: string },
  ) => {
    upcomingQueryArgs(establishmentId, viewMode, options)
    return upcomingQueryMock()
  },
  usePinActionPlanExecutionMutation: () => ({
    mutate: pinControl.pin,
    isPending: false,
  }),
  useUnpinActionPlanExecutionMutation: () => ({
    mutate: pinControl.unpin,
    isPending: false,
  }),
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    route: { kind: 'static', path: serializeAppRouteMockPath },
    search: upcomingRouteState.search,
    navigate: upcomingNavigate,
  }),
  serializeAppRoute: () => serializeAppRouteMockPath,
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

function renderUpcomingPage(props: { source?: 'establishment' | 'cross' } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ExecutionUpcomingPage, {
        onOpenActionPlanExecution,
        ...props,
      }),
    ),
  )
}

describe('ExecutionUpcomingPage', () => {
  beforeEach(() => {
    onOpenActionPlanExecution.mockClear()
    upcomingQueryMock.mockReturnValue(buildUpcomingQueryState())
    upcomingQueryArgs.mockClear()
    upcomingNavigate.mockClear()
    upcomingRouteState.search = ''
    serializeAppRouteMockPath = '/execution/upcoming'
    pinControl.failPin = false
    pinControl.pin.mockClear()
    pinControl.unpin.mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('renders the desktop row with Début/Fin under badges on web lg', () => {
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
    const pin = screen.getByRole('button', { name: 'Épingler' })
    expect(openControl.contains(pin)).toBe(false)
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.queryByText(/^Début : /)).toBeNull()
    expect(screen.queryByText(/Échéance/)).toBeNull()
    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.getByText('Alice Martin')).toBeTruthy()

    fireEvent.click(pin)
    expect(onOpenActionPlanExecution).not.toHaveBeenCalled()
    expect(pinControl.pin).toHaveBeenCalledWith('plan-all-day', expect.any(Object))
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()

    fireEvent.click(openControl)
    expect(onOpenActionPlanExecution).toHaveBeenCalledWith('plan-all-day')
  })

  it('pins successfully from the desktop upcoming row control', async () => {
    stubLgViewport(true)
    renderUpcomingPage()

    fireEvent.click(screen.getByRole('button', { name: 'Épingler' }))

    expect(pinControl.pin).toHaveBeenCalledWith('plan-scheduled', expect.any(Object))
    await waitFor(() => {
      expect(screen.queryByText('Épinglage impossible.')).toBeNull()
    })
  })

  it('shows a pin error on desktop upcoming, then clears it after a successful pin', () => {
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

    const [firstPin, secondPin] = screen.getAllByRole('button', { name: 'Épingler' })
    fireEvent.click(firstPin)

    expect(screen.getByText('Épinglage impossible.')).toBeTruthy()

    pinControl.failPin = false
    fireEvent.click(secondPin)
    expect(screen.queryByText('Épinglage impossible.')).toBeNull()
  })

  it('keeps the scheduled card and the actions sheet outside desktop web', () => {
    stubLgViewport(false)
    renderUpcomingPage()

    const openControl = screen.getByRole('button', { name: /Plan programmé/ })
    const pin = screen.getByRole('button', { name: 'Épingler' })
    expect(openControl.contains(pin)).toBe(true)
    expect(screen.getByText(/Début/)).toBeTruthy()
    expect(screen.queryByText(/^Début : /)).toBeNull()

    fireEvent.click(pin)
    expect(onOpenActionPlanExecution).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
  })

  it('defaults cross upcoming to Vue globale without a view_mode query', () => {
    serializeAppRouteMockPath = '/cross/execution/upcoming'
    renderUpcomingPage({ source: 'cross' })

    expect(upcomingQueryArgs).toHaveBeenCalledWith('est-1', 'general', { source: 'cross' })
    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe(
      'true',
    )
  })

  it('keeps an explicit personal view_mode on cross upcoming', () => {
    serializeAppRouteMockPath = '/cross/execution/upcoming'
    upcomingRouteState.search = '?view_mode=personal'
    renderUpcomingPage({ source: 'cross' })

    expect(upcomingQueryArgs).toHaveBeenCalledWith('est-1', 'personal', { source: 'cross' })
    expect(screen.getByRole('tab', { name: 'Ma vue' }).getAttribute('aria-selected')).toBe('true')
  })

  it('writes view_mode on the upcoming URL when the tab changes', () => {
    renderUpcomingPage()
    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    expect(upcomingNavigate).toHaveBeenCalledWith('/execution/upcoming?view_mode=general', {
      replace: true,
    })
  })

  it('keeps the scheduled card on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    renderUpcomingPage()

    const openControl = screen.getByRole('button', { name: /Plan programmé/ })
    const pin = screen.getByRole('button', { name: 'Épingler' })
    expect(openControl.contains(pin)).toBe(true)
    expect(screen.getByText(/Début/)).toBeTruthy()
    fireEvent.click(pin)
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
  })
})
