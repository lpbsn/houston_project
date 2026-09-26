// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItemWrapper } from '@/features/action-plans/types'
import { useTerrainHubTitleSlotValue } from '@/components/layout/terrain-hub-title-slot'
import { ActionPlansApiError } from '@/features/action-plans/api'

import {
  clearExecutionFeedReadingMemory,
  executionFeedReadingScopeKey,
  readExecutionFeedReading,
} from '../lib/execution-feed-reading-memory'
import { ExecutionFeedPage } from './execution-feed-page'

const planFetchNextPage = vi.fn()
const planFeedQueryMock = vi.fn()
const calendarQueryMock = vi.fn()
const upcomingQueryMock = vi.fn()
const executionNavigate = vi.fn()
const permissionHintsHolder = vi.hoisted(() => ({
  value: {} as {
    can_create_action_plan?: boolean
    can_view_action_plan_catalog?: boolean
  },
}))
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
const executionRouteState = { search: '' }
let serializeAppRouteMockPath = '/execution'

function buildPlanFeedWrapper(
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
      status: 'in_progress',
      requires_validation: false,
      validated_at: null,
      validated_by_display_name: null,
      pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
      involved_poles: [],
      signal_summary: null,
      assignees: [{ membership_id: 'member-1', display_name: 'Alice' }],
      start_at: null,
      end_at: null,
      all_day: false,
      visible_from: null,
      is_overdue: false,
      task_count: 0,
      treated_task_count: 0,
      task_executions: [],
      last_activity_at: '2026-06-13T12:00:00Z',
      created_at: '2026-06-13T12:00:00Z',
      created_by_display_name: 'Alice Martin',
      marked_done_at: null,
      marked_done_by_display_name: null,
      canceled_at: null,
      active_review: null,
      is_pinned: false,
      permission_hints: {
        can_mark_done: true,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_update: false,
        is_pilot_pole_assignee: true,
        can_pin: true,
      },
      ...overrides,
    },
  }
}

function deriveSectionCountsFromWrappers(
  items: ActionPlanExecutionFeedItemWrapper[],
): {
  pinned: number
  pending_validation: number
  overdue: number
  in_progress: number
  done: number
  canceled: number
} {
  const counts = {
    pinned: 0,
    pending_validation: 0,
    overdue: 0,
    in_progress: 0,
    done: 0,
    canceled: 0,
  }
  for (const wrapper of items) {
    const item = wrapper.action_plan_execution
    if (item.is_pinned) {
      counts.pinned += 1
      continue
    }
    if (item.status === 'pending_validation') {
      counts.pending_validation += 1
    } else if (item.status === 'in_progress') {
      if (item.is_overdue) {
        counts.overdue += 1
      } else {
        counts.in_progress += 1
      }
    } else if (item.status === 'done') {
      counts.done += 1
    } else if (item.status === 'canceled') {
      counts.canceled += 1
    }
  }
  return counts
}

function buildPlanFeedQueryState(overrides: Record<string, unknown> = {}) {
  const base = {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: planFetchNextPage,
    refetch: vi.fn(),
    data: {
      pages: [
        {
          items: [],
          scheduled_items: [],
          scheduled_count: 0,
          section_counts: {
            pinned: 0,
            pending_validation: 0,
            overdue: 0,
            in_progress: 0,
            done: 0,
            canceled: 0,
          },
          next_cursor: null,
          has_more: false,
        },
      ],
    },
  }
  const merged = { ...base, ...overrides } as typeof base & Record<string, unknown>
  const data = merged.data as
    | {
        pages?: Array<{
          items?: ActionPlanExecutionFeedItemWrapper[]
          section_counts?: ReturnType<typeof deriveSectionCountsFromWrappers>
          [key: string]: unknown
        }>
      }
    | undefined
  if (data?.pages) {
    merged.data = {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        section_counts:
          page.section_counts ?? deriveSectionCountsFromWrappers(page.items ?? []),
      })),
    }
  }
  return merged
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

vi.mock('@/features/auth/lib/bootstrap-permission-hints', () => ({
  getBootstrapPermissionHints: () => permissionHintsHolder.value,
}))

vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionFeedQuery: () => planFeedQueryMock(),
  useActionPlanExecutionCalendarQuery: () => calendarQueryMock(),
  useActionPlanExecutionUpcomingQuery: (
    _establishmentId: string | null | undefined,
    _viewMode: string,
    options?: { enabled?: boolean; pageSize?: number; source?: string },
  ) => upcomingQueryMock(options),
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
    route: { kind: 'static', path: '/execution' },
    search: executionRouteState.search,
    navigate: executionNavigate,
  }),
  serializeAppRoute: () => serializeAppRouteMockPath,
}))

function buildCalendarQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isFetching: false,
    isError: false,
    isSuccess: true,
    data: { timezone: 'Europe/Paris', items: [], unplanned: [] },
    refetch: vi.fn(),
    error: null,
    ...overrides,
  }
}

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

function TitleSlotProbe() {
  const node = useTerrainHubTitleSlotValue()
  return createElement('div', { 'data-testid': 'title-slot' }, node)
}

function renderExecutionFeedPage(
  props: {
    onNavigate?: (pathname: string) => void
    source?: 'establishment' | 'cross'
    establishmentId?: string | null
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const tree = (
    nextProps: {
      onNavigate?: (pathname: string) => void
      source?: 'establishment' | 'cross'
      establishmentId?: string | null
    } = props,
  ) =>
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement('div', null, createElement(TitleSlotProbe), createElement(ExecutionFeedPage, nextProps)),
    )

  const view = render(tree())
  return {
    ...view,
    rerenderPage: (
      nextProps: {
        onNavigate?: (pathname: string) => void
        source?: 'establishment' | 'cross'
        establishmentId?: string | null
      } = props,
    ) => view.rerender(tree(nextProps)),
  }
}

describe('ExecutionFeedPage plan feed', () => {
  beforeEach(() => {
    planFetchNextPage.mockClear()
    executionNavigate.mockClear()
    executionRouteState.search = ''
    serializeAppRouteMockPath = '/execution'
    planFeedQueryMock.mockReturnValue(buildPlanFeedQueryState())
    calendarQueryMock.mockReturnValue(buildCalendarQueryState())
    upcomingQueryMock.mockImplementation((options?: { enabled?: boolean; pageSize?: number }) => ({
      isLoading: false,
      isError: false,
      isSuccess: Boolean(options?.enabled),
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      refetch: vi.fn(),
      data: options?.enabled
        ? {
            pages: [
              {
                items: [
                  buildPlanFeedWrapper('plan-upcoming-1', 'Plan à venir lazy', {
                    status: 'scheduled',
                    start_at: '2026-07-13T12:00:00Z',
                  }),
                ],
                next_cursor: null,
                has_more: false,
              },
            ],
          }
        : undefined,
    }))
    permissionHintsHolder.value = {}
    pinControl.failPin = false
    pinControl.pin.mockClear()
    pinControl.unpin.mockClear()
    upcomingQueryMock.mockClear()
    clearExecutionFeedReadingMemory()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
    permissionHintsHolder.value = {}
    clearExecutionFeedReadingMemory()
  })

  it('renders plan execution items', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-1', 'Plan opérationnel')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Plan opérationnel')).toBeTruthy()
  })

  it('shows plan feed error state', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        isSuccess: false,
        isError: true,
        error: new ActionPlansApiError({
          status: 500,
          detail: 'Impossible de charger les plans d’action.',
        }),
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Impossible de charger les plans d’action.')).toBeTruthy()
  })

  it('shows load more button and calls fetchNextPage', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        hasNextPage: true,
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-1', 'Plan opérationnel')],
              next_cursor: 'plan-cursor',
              has_more: true,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    fireEvent.click(screen.getByRole('button', { name: 'Afficher plus' }))
    expect(planFetchNextPage).toHaveBeenCalledTimes(1)
  })

  it('concatenates items across pages', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-1', 'Plan un')],
              next_cursor: 'cursor-1',
              has_more: true,
            },
            {
              items: [buildPlanFeedWrapper('plan-2', 'Plan deux')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Plan un')).toBeTruthy()
    expect(screen.getByText('Plan deux')).toBeTruthy()
  })

  it('keeps empty state when all pages are empty', () => {
    renderExecutionFeedPage()

    expect(screen.getByText('Aucune exécution')).toBeTruthy()
  })

  it('shows section headers from section_counts before matching items are loaded', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        hasNextPage: true,
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-active', 'Plan actif')],
              scheduled_items: [],
              scheduled_count: 0,
              section_counts: {
                pinned: 0,
                pending_validation: 0,
                overdue: 0,
                in_progress: 1,
                done: 4,
                canceled: 0,
              },
              next_cursor: 'cursor-1',
              has_more: true,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: 'Replier la section En cours' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Déplier la section Terminés' })).toBeTruthy()
    expect(screen.getByText('Plan actif')).toBeTruthy()
    expect(screen.queryByText('Aucune exécution')).toBeNull()
    expect(screen.queryByText(/aucun terminé/i)).toBeNull()
    expect(screen.getByRole('button', { name: 'Afficher plus' })).toBeTruthy()
  })

  it('renders pinned items before section labels', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildPlanFeedWrapper('plan-pinned', 'Plan épinglé', { is_pinned: true }),
                buildPlanFeedWrapper('plan-regular', 'Plan normal'),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    const pinned = screen.getByText('Plan épinglé')
    const sectionToggle = screen.getByRole('button', { name: 'Replier la section En cours' })
    const regular = screen.getByText('Plan normal')

    expect(pinned.compareDocumentPosition(sectionToggle) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(sectionToggle.compareDocumentPosition(regular) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('keeps the done section collapsed by default', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildPlanFeedWrapper('plan-done', 'Plan terminé', { status: 'done' }),
                buildPlanFeedWrapper('plan-active', 'Plan actif'),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: 'Déplier la section Terminés' })).toBeTruthy()
    expect(screen.queryByText('Plan terminé')).toBeNull()
    expect(screen.getByText('Plan actif')).toBeTruthy()
  })

  it('keeps the canceled section collapsed by default', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildPlanFeedWrapper('plan-canceled', 'Plan annulé', { status: 'canceled' }),
                buildPlanFeedWrapper('plan-active', 'Plan actif'),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: 'Déplier la section Annulés' })).toBeTruthy()
    expect(screen.queryByText('Plan annulé')).toBeNull()
    expect(screen.getByText('Plan actif')).toBeTruthy()
  })

  it('collapses an expanded section when its header is toggled', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-active', 'Plan actif')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Plan actif')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Replier la section En cours' }))

    expect(screen.queryByText('Plan actif')).toBeNull()
    expect(screen.getByRole('button', { name: 'Déplier la section En cours' })).toBeTruthy()
  })

  it('shows loading more label while fetching next page', () => {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        hasNextPage: true,
        isFetchingNextPage: true,
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-1', 'Plan opérationnel')],
              next_cursor: 'cursor-1',
              has_more: true,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: 'Chargement…' })).toBeTruthy()
  })

  it('renders Planifiés on mobile without À venir nav', () => {
    const onNavigate = vi.fn()
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-active', 'Plan actif')],
              scheduled_items: [
                buildPlanFeedWrapper('plan-scheduled', 'Plan programmé', {
                  status: 'scheduled',
                  start_at: '2026-07-20T09:00:00Z',
                  permission_hints: {
                    can_mark_done: false,
                    can_validate: false,
                    can_reopen: false,
                    can_cancel: true,
                    can_update: false,
                    is_pilot_pole_assignee: false,
                    can_pin: false,
                  },
                }),
              ],
              scheduled_count: 4,
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage({ onNavigate })

    expect(screen.queryByRole('button', { name: 'À venir, 4' })).toBeNull()
    expect(screen.queryByRole('button', { name: /section Planifiées/ })).toBeNull()
    const planifiees = screen.getByRole('button', { name: 'Planifiés, 4' })
    expect(planifiees).toBeTruthy()
    expect(screen.getByText(/Prochaine :/)).toBeTruthy()
    fireEvent.click(planifiees)
    expect(onNavigate).toHaveBeenCalledWith('/execution/upcoming')
  })

  it('keeps empty state without À venir on mobile when nothing is scheduled', () => {
    const onNavigate = vi.fn()
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [],
              scheduled_items: [],
              scheduled_count: 0,
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage({ onNavigate })

    expect(screen.getByText('Aucune exécution')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /À venir/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Planifiés/ })).toBeNull()
  })

  it('switches from list to calendar via URL state', () => {
    renderExecutionFeedPage()
    fireEvent.click(screen.getByRole('tab', { name: 'Calendrier' }))
    expect(executionNavigate).toHaveBeenCalledWith(
      expect.stringContaining('layout=calendar'),
      { replace: true },
    )
  })

  it('exposes segmented layout and granularity tablists', () => {
    executionRouteState.search = '?layout=calendar&granularity=week&anchor=2026-09-08'
    renderExecutionFeedPage()
    expect(screen.getByRole('tablist', { name: 'Disposition du feed' })).toBeTruthy()
    expect(screen.getByRole('tablist', { name: 'Granularité du calendrier' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Semaine' }).getAttribute('aria-selected')).toBe('true')
  })

  it('opens a calendar event with the current feed search on the detail href', () => {
    stubLgViewport(true)
    executionRouteState.search =
      '?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=general'
    calendarQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: {
        timezone: 'Europe/Paris',
        items: [
          buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
            start_at: '2026-09-08T07:00:00.000Z',
            end_at: '2026-09-08T09:00:00.000Z',
          }),
        ],
        unplanned: [],
      },
      refetch: vi.fn(),
    })

    renderExecutionFeedPage()
    fireEvent.click(screen.getByRole('button', { name: /Brief cuisine/ }))

    expect(executionNavigate).toHaveBeenCalledWith(
      '/action-plans/executions/exec-cal?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=general',
    )
  })

  it('uses the live search after a search-only change with a stable route', () => {
    calendarQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: {
        timezone: 'Europe/Paris',
        items: [
          buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
            start_at: '2026-09-08T07:00:00.000Z',
            end_at: '2026-09-08T09:00:00.000Z',
          }),
        ],
        unplanned: [],
      },
      refetch: vi.fn(),
    })

    executionRouteState.search = ''
    const view = renderExecutionFeedPage()
    executionRouteState.search =
      '?layout=calendar&granularity=month&anchor=2026-09-08&view_mode=general'
    view.rerenderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brief cuisine/ }))
    expect(executionNavigate).toHaveBeenCalledWith(
      '/action-plans/executions/exec-cal?layout=calendar&granularity=month&anchor=2026-09-08&view_mode=general',
    )
  })

  it('exposes calendar and view-mode controls on the cross feed with Vue globale by default', () => {
    serializeAppRouteMockPath = '/cross/execution'
    renderExecutionFeedPage({ source: 'cross' })
    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByRole('tablist', { name: 'Disposition du feed' })).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: 'Calendrier' }))
    expect(executionNavigate).toHaveBeenCalledWith(
      expect.stringContaining('layout=calendar'),
      { replace: true },
    )
    expect(executionNavigate.mock.calls[0]?.[0]).not.toContain('view_mode=personal')
  })

  it('opens a cross calendar event while preserving Ma vue', () => {
    stubLgViewport(true)
    serializeAppRouteMockPath = '/cross/execution'
    executionRouteState.search =
      '?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=personal'
    calendarQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: {
        timezone: 'Europe/Paris',
        items: [
          buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
            start_at: '2026-09-08T07:00:00.000Z',
            end_at: '2026-09-08T09:00:00.000Z',
          }),
        ],
        unplanned: [],
      },
      refetch: vi.fn(),
    })

    renderExecutionFeedPage({ source: 'cross' })
    fireEvent.click(screen.getByRole('button', { name: /Brief cuisine/ }))
    expect(executionNavigate).toHaveBeenCalledWith(
      '/cross/execution/exec-cal?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=personal',
    )
  })

  it('keeps calendar chrome when navigating to an uncached period', () => {
    stubLgViewport(true)
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        data: {
          timezone: 'Europe/Paris',
          items: [
            buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        },
      }),
    )
    const view = renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()

    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-09'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isLoading: true,
        isFetching: true,
        isSuccess: false,
        data: undefined,
      }),
    )
    view.rerenderPage()

    expect(screen.getByTestId('calendar-weekday-2026-09-09')).toBeTruthy()
    expect(screen.getByTestId('calendar-period-pending')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Brief cuisine/ })).toBeNull()
    expect(screen.queryByText('Chargement du calendrier…')).toBeNull()
  })

  it('does not show period pending during a background refetch of the current key', () => {
    stubLgViewport(true)
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isFetching: true,
        isLoading: false,
        data: {
          timezone: 'Europe/Paris',
          items: [
            buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: /Brief cuisine/ })).toBeTruthy()
    expect(screen.queryByTestId('calendar-period-pending')).toBeNull()
    expect(screen.queryByText('Chargement du calendrier…')).toBeNull()
  })

  it('keeps the initial calendar fetch as a full-page loading message', () => {
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isLoading: true,
        isFetching: true,
        isSuccess: false,
        data: undefined,
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Chargement du calendrier…')).toBeTruthy()
    expect(screen.queryByTestId('calendar-time-scroller')).toBeNull()
    expect(screen.queryByTestId('calendar-period-pending')).toBeNull()
  })

  it('shows retry on the selected period when a later calendar fetch fails', () => {
    stubLgViewport(true)
    const refetch = vi.fn()
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        refetch,
        data: {
          timezone: 'Europe/Paris',
          items: [
            buildPlanFeedWrapper('exec-cal', 'Brief cuisine', {
              start_at: '2026-09-08T07:00:00.000Z',
              end_at: '2026-09-08T09:00:00.000Z',
            }),
          ],
          unplanned: [],
        },
      }),
    )
    const view = renderExecutionFeedPage()

    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-09'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isLoading: false,
        isSuccess: false,
        isError: true,
        data: undefined,
        refetch,
        error: new ActionPlansApiError({
          status: 500,
          detail: 'Impossible de charger le calendrier.',
        }),
      }),
    )
    view.rerenderPage()

    expect(screen.getByTestId('calendar-weekday-2026-09-09')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Brief cuisine/ })).toBeNull()
    expect(screen.getByTestId('calendar-period-error')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('keeps Aujourd’hui on the last known calendar timezone while a period has no data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-08T22:30:00.000Z'))
    stubLgViewport(true)
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        data: { timezone: 'UTC', items: [], unplanned: [] },
      }),
    )
    const view = renderExecutionFeedPage()

    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-01'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isLoading: true,
        isFetching: true,
        isSuccess: false,
        data: undefined,
      }),
    )
    view.rerenderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Aujourd’hui' }))
    expect(executionNavigate).toHaveBeenCalledWith(
      expect.stringContaining('anchor=2026-09-08'),
      { replace: true },
    )
  })

  it('does not reuse a remembered timezone after an establishment change', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-08T22:30:00.000Z'))
    stubLgViewport(true)
    executionRouteState.search = '?layout=calendar&granularity=day&anchor=2026-09-08'
    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        data: { timezone: 'UTC', items: [], unplanned: [] },
      }),
    )
    const view = renderExecutionFeedPage({ establishmentId: 'est-1' })

    calendarQueryMock.mockReturnValue(
      buildCalendarQueryState({
        isLoading: true,
        isFetching: true,
        isSuccess: false,
        data: undefined,
      }),
    )
    view.rerenderPage({ establishmentId: 'est-2' })

    fireEvent.click(screen.getByRole('button', { name: 'Aujourd’hui' }))
    expect(executionNavigate).toHaveBeenCalledWith(
      expect.stringContaining('anchor=2026-09-09'),
      { replace: true },
    )
  })
})

describe('ExecutionFeedPage desktop list', () => {
  beforeEach(() => {
    planFetchNextPage.mockClear()
    executionNavigate.mockClear()
    executionRouteState.search = ''
    serializeAppRouteMockPath = '/execution'
    permissionHintsHolder.value = {}
    clearExecutionFeedReadingMemory()
    calendarQueryMock.mockReturnValue(buildCalendarQueryState())
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
    permissionHintsHolder.value = {}
    clearExecutionFeedReadingMemory()
  })

  function showOperationalFeed() {
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildPlanFeedWrapper('plan-active', 'Plan actif', {
                  task_count: 4,
                  treated_task_count: 1,
                }),
                buildPlanFeedWrapper('plan-done', 'Plan terminé', { status: 'done' }),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )
  }

  it('pins from the direct control without opening the detail on desktop web', () => {
    stubLgViewport(true)
    showOperationalFeed()
    renderExecutionFeedPage()

    const openControl = screen.getByRole('button', { name: /Plan actif/ })
    const pin = screen.getByRole('button', { name: 'Épingler' })
    expect(openControl.contains(pin)).toBe(false)
    fireEvent.click(pin)
    expect(executionNavigate).not.toHaveBeenCalled()
    expect(pinControl.pin).toHaveBeenCalledWith('plan-active', expect.any(Object))
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
    expect(screen.queryByRole('menu', { name: 'Actions du plan d’action' })).toBeNull()
    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.queryByText(/Tâches complétées/)).toBeNull()
    expect(screen.getByText('Alice Martin')).toBeTruthy()
  })

  it('pins successfully from the desktop row control', async () => {
    stubLgViewport(true)
    showOperationalFeed()
    renderExecutionFeedPage()

    fireEvent.click(screen.getByRole('button', { name: 'Épingler' }))

    expect(pinControl.pin).toHaveBeenCalledWith('plan-active', expect.any(Object))
    await waitFor(() => {
      expect(screen.queryByRole('alert')).toBeNull()
    })
  })

  it('shows a pin error on desktop, then clears it after a successful pin on another row', () => {
    stubLgViewport(true)
    pinControl.failPin = true
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildPlanFeedWrapper('plan-active', 'Plan actif', {
                  task_count: 4,
                  treated_task_count: 1,
                }),
                buildPlanFeedWrapper('plan-other', 'Plan autre'),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )
    renderExecutionFeedPage()

    const [firstPin, secondPin] = screen.getAllByRole('button', { name: 'Épingler' })
    fireEvent.click(firstPin)

    expect(screen.getByText('Épinglage impossible.')).toBeTruthy()

    pinControl.failPin = false
    fireEvent.click(secondPin)
    expect(screen.queryByText('Épinglage impossible.')).toBeNull()
  })

  it('keeps the card and pin control on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    showOperationalFeed()
    renderExecutionFeedPage()

    const openControl = screen.getByRole('button', { name: /Plan actif/ })
    const pin = screen.getByRole('button', { name: 'Épingler' })
    expect(openControl.contains(pin)).toBe(true)
    fireEvent.click(pin)
    expect(executionNavigate).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
    expect(screen.queryByRole('menu', { name: 'Actions du plan d’action' })).toBeNull()
  })

  it('opens the existing create choices in a dialog without creating a plan', () => {
    stubLgViewport(true)
    permissionHintsHolder.value = {
      can_create_action_plan: true,
      can_view_action_plan_catalog: true,
    }
    const onNavigate = vi.fn()
    renderExecutionFeedPage({ onNavigate })

    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))
    expect(onNavigate).not.toHaveBeenCalled()
    expect(screen.getByTestId('execution-create-menu-dialog')).toBeTruthy()
    expect(screen.queryByTestId('execution-create-menu-sheet')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: "Créer un plan d'action" }))
    expect(onNavigate).toHaveBeenCalledWith('/action-plans/new?from=execution')
  })

  it('keeps a compact mobile create control and tight list/calendar toolbar padding', () => {
    stubLgViewport(false)
    permissionHintsHolder.value = {
      can_create_action_plan: true,
      can_view_action_plan_catalog: true,
    }
    renderExecutionFeedPage()

    const createButton = screen.getByRole('button', { name: 'Créer' })
    expect(createButton.className).toContain('size-11')
    expect(createButton.className).toContain('-m-2')
    expect(createButton.className).toContain('bg-transparent')
    const visualDisc = createButton.querySelector('span')
    expect(visualDisc?.className).toContain('size-7')
    expect(visualDisc?.className).toContain('bg-[#114660]')
    expect(createButton.querySelector('svg')?.classList.toString()).toContain('size-3.5')

    const layoutTabs = screen.getByRole('tablist', { name: 'Disposition du feed' })
    const toolbar = layoutTabs.parentElement?.parentElement
    expect(toolbar?.className).toContain('pt-0')
    expect(toolbar?.className).toContain('pb-0.5')
    expect(toolbar?.className).not.toContain('pt-0.5')
    expect(toolbar?.className).not.toContain('pb-1.5')
  })

  it('navigates from Planifiés compact row for the same scope', () => {
    stubLgViewport(false)
    const onNavigate = vi.fn()
    const scopeKey = executionFeedReadingScopeKey('establishment', 'est-1')
    planFeedQueryMock.mockReturnValue(
      buildPlanFeedQueryState({
        data: {
          pages: [
            {
              items: [buildPlanFeedWrapper('plan-active', 'Plan actif')],
              scheduled_items: [
                buildPlanFeedWrapper('plan-scheduled', 'Plan programmé', {
                  status: 'scheduled',
                  start_at: '2026-07-13T12:00:00Z',
                }),
              ],
              scheduled_count: 2,
              section_counts: {
                pinned: 0,
                pending_validation: 0,
                overdue: 0,
                in_progress: 1,
                done: 0,
                canceled: 0,
              },
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage({ establishmentId: 'est-1', onNavigate })
    fireEvent.click(screen.getByRole('button', { name: 'Planifiés, 2' }))
    expect(onNavigate).toHaveBeenCalledWith('/execution/upcoming')
    expect(readExecutionFeedReading(scopeKey)).toBeTruthy()
  })

  it('restores the open section and scroll after an internal remount of the same scope', () => {
    showOperationalFeed()
    const scopeKey = executionFeedReadingScopeKey('establishment', 'est-1')
    renderExecutionFeedPage({ establishmentId: 'est-1' })
    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Terminés' }))
    const scroller = screen.getByTestId('execution-feed-scroll')
    scroller.scrollTop = 120
    fireEvent.scroll(scroller)

    expect(readExecutionFeedReading(scopeKey)?.expandedByKey.done).toBe(true)
    expect(readExecutionFeedReading(scopeKey)?.scrollTop).toBe(120)

    cleanup()
    renderExecutionFeedPage({ establishmentId: 'est-1' })

    expect(screen.getByText('Plan terminé')).toBeTruthy()
    expect(screen.getByTestId('execution-feed-scroll').scrollTop).toBe(120)
  })

  it('starts another scope from its own reading state', () => {
    showOperationalFeed()
    renderExecutionFeedPage({ establishmentId: 'est-1' })
    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Terminés' }))
    const scroller = screen.getByTestId('execution-feed-scroll')
    scroller.scrollTop = 120
    fireEvent.scroll(scroller)

    cleanup()
    renderExecutionFeedPage({ establishmentId: 'est-2' })

    expect(screen.queryByText('Plan terminé')).toBeNull()
    expect(screen.getByTestId('execution-feed-scroll').scrollTop).toBe(0)
  })

  it('keeps reading state per establishment across A → B → A without unmounting', () => {
    showOperationalFeed()
    const view = renderExecutionFeedPage({ establishmentId: 'est-1' })
    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Terminés' }))
    const scrollerA = screen.getByTestId('execution-feed-scroll')
    scrollerA.scrollTop = 120
    fireEvent.scroll(scrollerA)

    expect(
      readExecutionFeedReading(executionFeedReadingScopeKey('establishment', 'est-1')),
    ).toMatchObject({
      expandedByKey: expect.objectContaining({ done: true }),
      scrollTop: 120,
    })

    view.rerenderPage({ establishmentId: 'est-2' })

    expect(screen.queryByText('Plan terminé')).toBeNull()
    expect(screen.getByTestId('execution-feed-scroll').scrollTop).toBe(0)
    expect(
      readExecutionFeedReading(executionFeedReadingScopeKey('establishment', 'est-1')),
    ).toMatchObject({
      expandedByKey: expect.objectContaining({ done: true }),
      scrollTop: 120,
    })
    expect(
      readExecutionFeedReading(executionFeedReadingScopeKey('establishment', 'est-2'))?.expandedByKey
        .done,
    ).not.toBe(true)

    view.rerenderPage({ establishmentId: 'est-1' })

    expect(screen.getByText('Plan terminé')).toBeTruthy()
    expect(screen.getByTestId('execution-feed-scroll').scrollTop).toBe(120)
    expect(
      readExecutionFeedReading(executionFeedReadingScopeKey('establishment', 'est-1')),
    ).toMatchObject({
      expandedByKey: expect.objectContaining({ done: true }),
      scrollTop: 120,
    })
  })
})
