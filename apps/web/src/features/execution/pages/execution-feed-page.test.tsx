// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ExecutionFeedItem } from '@/features/actions/types'
import { buildActionFeedItem } from '@/features/actions/test-fixtures'
import type { ActionPlanExecutionFeedItemWrapper } from '@/features/action-plans/types'
import { ActionPlansApiError } from '@/features/action-plans/api'

import { ExecutionFeedPage } from './execution-feed-page'

const legacyFetchNextPage = vi.fn()
const planFetchNextPage = vi.fn()

function buildActionItem(id: string): ExecutionFeedItem {
  return {
    item_type: 'action',
    action: buildActionFeedItem({
      id,
      title: `Action ${id}`,
      assignees: [
        {
          membership_id: 'member-staff',
          display_name: 'Staff',
          role: 'staff',
        },
      ],
      created_by_display_name: 'Owner',
      affected_business_unit_key: 'restaurant',
      affected_business_unit_label: 'Restaurant',
      responsible_business_unit_key: 'restaurant',
      responsible_business_unit_label: 'Restaurant',
      due_at: '2026-06-13T12:00:00Z',
      last_activity_at: '2026-06-13T12:00:00Z',
      created_at: '2026-06-13T12:00:00Z',
      permission_hints: {
        can_accept: true,
        can_mark_done: true,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_reassign: false,
        can_update_due_at: false,
        is_assignee: true,
        accepted_by_me: false,
      },
    }),
    checklist: null,
  }
}

function buildPlanFeedWrapper(id: string, title: string): ActionPlanExecutionFeedItemWrapper {
  return {
    item_type: 'action_plan_execution',
    action_plan_execution: {
      id,
      title,
      description_short: 'Description plan',
      status: 'in_progress',
      requires_validation: false,
      pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      involved_poles: [],
      signal_summary: null,
      assignees: [{ membership_id: 'member-1', display_name: 'Alice' }],
      end_at: null,
      is_overdue: false,
      task_executions: [],
      last_activity_at: '2026-06-13T12:00:00Z',
      created_at: '2026-06-13T12:00:00Z',
      permission_hints: {
        can_mark_done: true,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        is_pilot_pole_assignee: true,
      },
    },
  }
}

function buildLegacyFeedQueryState(
  overrides: Record<string, unknown> = {},
) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: legacyFetchNextPage,
    refetch: vi.fn(),
    data: {
      pages: [{ items: [], next_cursor: null, has_more: false }],
    },
    ...overrides,
  }
}

function buildPlanFeedQueryState(
  overrides: Record<string, unknown> = {},
) {
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

const legacyFeedQueryMock = vi.fn()
const planFeedQueryMock = vi.fn()

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

vi.mock('@/features/actions/hooks', () => ({
  useExecutionFeedQuery: () => legacyFeedQueryMock(),
}))

vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionFeedQuery: () => planFeedQueryMock(),
}))

function renderExecutionFeedPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ExecutionFeedPage, {}),
    ),
  )
}

describe('ExecutionFeedPage dual feed', () => {
  beforeEach(() => {
    legacyFetchNextPage.mockClear()
    planFetchNextPage.mockClear()
    legacyFeedQueryMock.mockReturnValue(buildLegacyFeedQueryState())
    planFeedQueryMock.mockReturnValue(buildPlanFeedQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  it('renders plan and legacy items together', () => {
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
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        data: {
          pages: [
            {
              items: [buildActionItem('action-1')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Plan opérationnel')).toBeTruthy()
    expect(screen.getByText('Action action-1')).toBeTruthy()
  })

  it('shows plan feed error without hiding legacy content', () => {
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
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        data: {
          pages: [
            {
              items: [buildActionItem('action-1')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Impossible de charger les plans d’action.')).toBeTruthy()
    expect(screen.getByText('Action action-1')).toBeTruthy()
  })

  it('calls fetchNextPage only on feeds with hasNextPage', () => {
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
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        hasNextPage: false,
        data: {
          pages: [
            {
              items: [buildActionItem('action-1')],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    fireEvent.click(screen.getByRole('button', { name: 'Charger plus' }))

    expect(planFetchNextPage).toHaveBeenCalledTimes(1)
    expect(legacyFetchNextPage).not.toHaveBeenCalled()
  })
})

describe('ExecutionFeedPage pagination', () => {
  beforeEach(() => {
    legacyFetchNextPage.mockClear()
    planFetchNextPage.mockClear()
    legacyFeedQueryMock.mockReturnValue(buildLegacyFeedQueryState())
    planFeedQueryMock.mockReturnValue(buildPlanFeedQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the first page items', () => {
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        data: {
          pages: [{ items: [buildActionItem('action-1')], next_cursor: null, has_more: false }],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getByText('Action action-1')).toBeTruthy()
  })

  it('shows load more button and calls fetchNextPage', () => {
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        hasNextPage: true,
        data: {
          pages: [
            {
              items: [buildActionItem('action-1')],
              next_cursor: 'cursor-1',
              has_more: true,
            },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    fireEvent.click(screen.getByRole('button', { name: 'Charger plus' }))
    expect(legacyFetchNextPage).toHaveBeenCalled()
  })

  it('concatenates items across pages', () => {
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        data: {
          pages: [
            { items: [buildActionItem('action-1')], next_cursor: 'cursor-1', has_more: true },
            { items: [buildActionItem('action-2')], next_cursor: null, has_more: false },
          ],
        },
      }),
    )

    renderExecutionFeedPage()

    expect(screen.getAllByText('Action action-1')).toHaveLength(1)
    expect(screen.getAllByText('Action action-2')).toHaveLength(1)
  })

  it('keeps empty state when all pages are empty', () => {
    renderExecutionFeedPage()

    expect(screen.getByText('Aucune exécution')).toBeTruthy()
  })

  it('shows loading more label while fetching next page', () => {
    legacyFeedQueryMock.mockReturnValue(
      buildLegacyFeedQueryState({
        hasNextPage: true,
        isFetchingNextPage: true,
        data: {
          pages: [
            {
              items: [buildActionItem('action-1')],
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
})
