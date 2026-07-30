// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItemWrapper } from '@/features/action-plans/types'
import { ActionPlansApiError } from '@/features/action-plans/api'

import { ExecutionFeedPage } from './execution-feed-page'

const planFetchNextPage = vi.fn()
const planFeedQueryMock = vi.fn()

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
      pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
      involved_poles: [],
      signal_summary: null,
      assignees: [{ membership_id: 'member-1', display_name: 'Alice' }],
      start_at: null,
      end_at: null,
      is_overdue: false,
      task_count: 0,
      treated_task_count: 0,
      task_executions: [],
      last_activity_at: '2026-06-13T12:00:00Z',
      created_at: '2026-06-13T12:00:00Z',
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

function buildPlanFeedQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: planFetchNextPage,
    refetch: vi.fn(),
    data: {
      pages: [{ items: [], next_cursor: null, has_more: false }],
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

vi.mock('@/features/auth/lib/bootstrap-permission-hints', () => ({
  getBootstrapPermissionHints: () => ({}),
}))

vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionFeedQuery: () => planFeedQueryMock(),
}))

vi.mock('@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions', () => ({
  useActionPlanExecutionFeedQuickActions: () => ({
    activeItem: null,
    actionsOpen: false,
    openActions: vi.fn(),
    closeActions: vi.fn(),
    runAction: vi.fn(),
    isPending: false,
  }),
}))

function renderExecutionFeedPage(props: { onNavigate?: (pathname: string) => void } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ExecutionFeedPage, props),
    ),
  )
}

describe('ExecutionFeedPage plan feed', () => {
  beforeEach(() => {
    planFetchNextPage.mockClear()
    planFeedQueryMock.mockReturnValue(buildPlanFeedQueryState())
  })

  afterEach(() => {
    cleanup()
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

    fireEvent.click(screen.getByRole('button', { name: 'Charger plus' }))
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

  it('renders Planifiées from scheduled_items and À venir nav with scheduled_count', () => {
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

    expect(screen.getByRole('button', { name: 'À venir, 4' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Replier la section Planifiées' })).toBeTruthy()
    expect(screen.getByText('Plan programmé')).toBeTruthy()
    expect(screen.getByText('Planifiée')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'À venir, 4' }))
    expect(onNavigate).toHaveBeenCalledWith('/execution/upcoming')
  })

  it('keeps À venir nav with count 0 when feed and scheduled preview are empty', () => {
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
    expect(screen.getByRole('button', { name: 'À venir, 0' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Replier la section Planifiées' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Déplier la section Planifiées' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'À venir, 0' }))
    expect(onNavigate).toHaveBeenCalledWith('/execution/upcoming')
  })
})
