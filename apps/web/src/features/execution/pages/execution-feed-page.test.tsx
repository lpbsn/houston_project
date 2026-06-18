// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ExecutionFeedItem } from '@/features/actions/types'
import { buildActionFeedItem } from '@/features/actions/test-fixtures'

import { ExecutionFeedPage } from './execution-feed-page'

const fetchNextPage = vi.fn()

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

const feedQueryMock = vi.fn()

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
  useExecutionFeedQuery: () => feedQueryMock(),
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

describe('ExecutionFeedPage pagination', () => {
  beforeEach(() => {
    fetchNextPage.mockClear()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the first page items', () => {
    feedQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage,
      data: {
        pages: [{ items: [buildActionItem('action-1')], next_cursor: null, has_more: false }],
      },
    })

    renderExecutionFeedPage()

    expect(screen.getByText('Action action-1')).toBeTruthy()
  })

  it('shows load more button and calls fetchNextPage', () => {
    feedQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
      data: {
        pages: [
          {
            items: [buildActionItem('action-1')],
            next_cursor: 'cursor-1',
            has_more: true,
          },
        ],
      },
    })

    renderExecutionFeedPage()

    const button = screen.getByRole('button', { name: 'Charger plus' })
    button.click()
    expect(fetchNextPage).toHaveBeenCalled()
  })

  it('concatenates items across pages', () => {
    feedQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage,
      data: {
        pages: [
          { items: [buildActionItem('action-1')], next_cursor: 'cursor-1', has_more: true },
          { items: [buildActionItem('action-2')], next_cursor: null, has_more: false },
        ],
      },
    })

    renderExecutionFeedPage()

    expect(screen.getAllByText('Action action-1')).toHaveLength(1)
    expect(screen.getAllByText('Action action-2')).toHaveLength(1)
  })

  it('keeps empty state when all pages are empty', () => {
    feedQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage,
      data: {
        pages: [{ items: [], next_cursor: null, has_more: false }],
      },
    })

    renderExecutionFeedPage()

    expect(screen.getByText('Aucune exécution')).toBeTruthy()
  })

  it('shows loading more label while fetching next page', () => {
    feedQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      isSuccess: true,
      hasNextPage: true,
      isFetchingNextPage: true,
      fetchNextPage,
      data: {
        pages: [
          {
            items: [buildActionItem('action-1')],
            next_cursor: 'cursor-1',
            has_more: true,
          },
        ],
      },
    })

    renderExecutionFeedPage()

    expect(screen.getByRole('button', { name: 'Chargement…' })).toBeTruthy()
  })
})
