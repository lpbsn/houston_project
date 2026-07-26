// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedItem } from '@/features/signals/types'

import { SignalFeedPage } from './signal-feed-page'

const feedFetchNextPage = vi.fn()
const feedQueryMock = vi.fn()

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: null,
    permission_hints: {
      can_pin: true,
      can_cancel: true,
      can_resolve: true,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
    },
    ...overrides,
  }
}

function buildFeedQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: feedFetchNextPage,
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

vi.mock('@/features/signals/hooks', () => ({
  useSignalFeedQuery: () => feedQueryMock(),
}))

vi.mock('@/features/signals/hooks/use-signal-feed-quick-actions', () => ({
  useSignalFeedQuickActions: () => ({
    activeItem: null,
    actionsOpen: false,
    openActions: vi.fn(),
    closeActions: vi.fn(),
    runAction: vi.fn(),
    isPending: false,
    actionError: null,
  }),
}))

vi.mock('@/features/signals/components/signal-feed-filters-bar', () => ({
  EMPTY_SIGNAL_FEED_FILTERS: {
    statuses: [],
    businessUnitIds: [],
    activitySubjectIds: [],
  },
  SignalFeedFiltersBar: () => null,
}))

function renderSignalFeedPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(SignalFeedPage, { onOpenSignal: vi.fn() }),
    ),
  )
}

describe('SignalFeedPage collapsible sections', () => {
  beforeEach(() => {
    feedFetchNextPage.mockClear()
    feedQueryMock.mockReturnValue(buildFeedQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  it('keeps terminal sections collapsed by default when multiple statuses are present', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' }),
                buildFeedItem({ id: 'signal-resolved', title: 'Signal résolu', status: 'resolved' }),
                buildFeedItem({ id: 'signal-canceled', title: 'Signal annulé', status: 'canceled' }),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderSignalFeedPage()

    expect(screen.getByRole('button', { name: 'Déplier la section Résolues' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Déplier la section Annulées' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Signal ouvert' })).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 3, name: 'Signal résolu' })).toBeNull()
    expect(screen.queryByRole('heading', { level: 3, name: 'Signal annulé' })).toBeNull()
  })

  it('collapses an expanded section when its header is toggled', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          pages: [
            {
              items: [
                buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' }),
                buildFeedItem({ id: 'signal-progress', title: 'Signal en cours', status: 'in_progress' }),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderSignalFeedPage()

    expect(screen.getByRole('heading', { level: 3, name: 'Signal ouvert' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Replier la section En attente' }))

    expect(screen.queryByRole('heading', { level: 3, name: 'Signal ouvert' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Déplier la section En attente' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
  })
})
