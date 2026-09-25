// @vitest-environment jsdom

import { createElement, useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import type { SignalFeedItem } from '@/features/signals/types'

import {
  clearSignalFeedReadingMemory,
  readSignalFeedReading,
  signalFeedReadingScopeKey,
  writeSignalFeedReading,
} from '../lib/signal-feed-reading-memory'
import type { SignalFeedItem as FeedItemForActions } from '../types'

import { SignalFeedPage } from './signal-feed-page'

const feedLoadMoreMutate = vi.fn()
const feedQueryMock = vi.fn()
const loadMoreMock = vi.fn()
const feedQueryCalls: unknown[][] = []

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
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
    resolution_request: null,
    permission_hints: {
      can_pin: true,
      can_mark_interesting: false,
      can_cancel: true,
      can_resolve: true,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
      can_request_resolution: false,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
    },
    ...overrides,
  }
}

function buildFeedQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    refetch: vi.fn(),
    data: {
      sections: [] as Array<{
        status: string
        items: SignalFeedItem[]
        next_cursor: string | null
        has_more: boolean
      }>,
      applied_filters: {},
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
  useSignalFeedQuery: (...args: unknown[]) => {
    feedQueryCalls.push(args)
    return feedQueryMock()
  },
  useLoadMoreSignalFeedSection: () => loadMoreMock(),
}))

vi.mock('@/features/signals/hooks/use-signal-feed-quick-actions', () => ({
  useSignalFeedQuickActions: () => {
    const [activeItem, setActiveItem] = useState<FeedItemForActions | null>(null)
    const [actionsOpen, setActionsOpen] = useState(false)
    return {
      activeItem,
      actionsOpen,
      openActions: (item: FeedItemForActions) => {
        setActiveItem(item)
        setActionsOpen(true)
      },
      closeActions: () => {
        setActionsOpen(false)
        setActiveItem(null)
      },
      runAction: vi.fn(() => 'close' as const),
      isPending: false,
      actionError: null,
    }
  },
}))

vi.mock('@/features/signals/components/signal-feed-filters-bar', () => ({
  EMPTY_SIGNAL_FEED_FILTERS: {
    statuses: [],
    businessUnitIds: [],
    activitySubjectIds: [],
    needsQualification: false,
  },
  SignalFeedFiltersBar: () => null,
}))

function renderSignalFeedPage(
  props: {
    onOpenSignal?: (signalId: string) => void
    establishmentId?: string | null
    source?: 'establishment' | 'cross'
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(TerrainTopbar, { variant: 'hub', pageTitle: 'Observations' }),
      createElement(SignalFeedPage, {
        onOpenSignal: props.onOpenSignal ?? vi.fn(),
        establishmentId: props.establishmentId,
        source: props.source,
      }),
    ),
  )
}

function mockLgViewport(matches: boolean) {
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

function openSectionsFeed() {
  feedQueryMock.mockReturnValue(
    buildFeedQueryState({
      data: {
        sections: [
          {
            status: 'open',
            items: [buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' })],
            next_cursor: null,
            has_more: false,
          },
          {
            status: 'resolved',
            items: [
              buildFeedItem({
                id: 'signal-resolved',
                title: 'Signal résolu',
                status: 'resolved',
              }),
            ],
            next_cursor: null,
            has_more: false,
          },
        ],
      },
    }),
  )
}

describe('SignalFeedPage collapsible sections', () => {
  beforeEach(() => {
    feedLoadMoreMutate.mockClear()
    feedQueryCalls.length = 0
    clearSignalFeedReadingMemory()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      variables: undefined,
    })
    feedQueryMock.mockReturnValue(buildFeedQueryState())
  })

  afterEach(() => {
    cleanup()
    clearSignalFeedReadingMemory()
    vi.unstubAllEnvs()
  })

  it('keeps terminal sections collapsed by default when multiple statuses are present', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          sections: [
            {
              status: 'open',
              items: [buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' })],
              next_cursor: null,
              has_more: false,
            },
            {
              status: 'resolved',
              items: [
                buildFeedItem({ id: 'signal-resolved', title: 'Signal résolu', status: 'resolved' }),
              ],
              next_cursor: null,
              has_more: false,
            },
            {
              status: 'canceled',
              items: [
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
          sections: [
            {
              status: 'open',
              items: [buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' })],
              next_cursor: null,
              has_more: false,
            },
            {
              status: 'in_progress',
              items: [
                buildFeedItem({
                  id: 'signal-progress',
                  title: 'Signal en cours',
                  status: 'in_progress',
                }),
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

  it('shows later sections and per-section load more when open still has more', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          sections: [
            {
              status: 'open',
              items: [
                buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' }),
              ],
              next_cursor: 'open-cursor',
              has_more: true,
            },
            {
              status: 'resolved',
              items: [
                buildFeedItem({ id: 'signal-resolved', title: 'Signal résolu', status: 'resolved' }),
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
    expect(screen.getByRole('button', { name: 'Déplier la section Résolues' })).toBeTruthy()
    const loadMore = screen.getByRole('button', { name: 'Charger plus' })
    fireEvent.click(loadMore)
    expect(feedLoadMoreMutate).toHaveBeenCalledWith('open')
  })

  it('keeps open load more when every loaded open item is pinned', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          sections: [
            {
              status: 'open',
              items: [
                buildFeedItem({
                  id: 'pinned-open',
                  title: 'Épinglée ouverte',
                  status: 'open',
                  is_pinned: true,
                }),
              ],
              next_cursor: 'open-cursor',
              has_more: true,
            },
            {
              status: 'resolved',
              items: [
                buildFeedItem({ id: 'signal-resolved', title: 'Signal résolu', status: 'resolved' }),
              ],
              next_cursor: null,
              has_more: false,
            },
          ],
        },
      }),
    )

    renderSignalFeedPage()

    expect(screen.getByRole('heading', { level: 3, name: 'Épinglée ouverte' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Replier la section En attente' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Charger plus' }))
    expect(feedLoadMoreMutate).toHaveBeenCalledWith('open')
  })
})

describe('SignalFeedPage reading restoration', () => {
  beforeEach(() => {
    feedQueryCalls.length = 0
    clearSignalFeedReadingMemory()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      variables: undefined,
    })
    openSectionsFeed()
  })

  afterEach(() => {
    cleanup()
    clearSignalFeedReadingMemory()
    vi.unstubAllEnvs()
  })

  it('restores view, filters, open section and scroll after an internal remount of the same scope', () => {
    const scopeKey = signalFeedReadingScopeKey('establishment', 'est-1')
    renderSignalFeedPage()
    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    fireEvent.click(screen.getByRole('button', { name: 'Déplier la section Résolues' }))
    const scroller = screen.getByTestId('signal-feed-scroll')
    scroller.scrollTop = 140
    fireEvent.scroll(scroller)

    expect(readSignalFeedReading(scopeKey)?.viewMode).toBe('general')
    expect(readSignalFeedReading(scopeKey)?.expandedByKey.resolved).toBe(true)
    expect(readSignalFeedReading(scopeKey)?.scrollTop).toBe(140)

    cleanup()
    renderSignalFeedPage()

    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByRole('heading', { level: 3, name: 'Signal résolu' })).toBeTruthy()
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(140)
  })

  it('starts the other scope from its own reading state', () => {
    writeSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'), {
      viewMode: 'general',
      filters: {
        statuses: ['open'],
        businessUnitIds: [],
        activitySubjectIds: [],
        needsQualification: false,
      },
      expandedByKey: { resolved: true },
      scrollTop: 90,
    })

    renderSignalFeedPage({ establishmentId: 'est-2' })

    expect(screen.getByRole('tab', { name: 'Ma zone' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.queryByRole('heading', { level: 3, name: 'Signal résolu' })).toBeNull()
    const establishmentCall = feedQueryCalls.find((call) => call[0] === 'est-2')
    expect(establishmentCall?.[1]).toBe('personal')
    expect(establishmentCall?.[2]).toMatchObject({ statuses: [] })
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(0)
  })

  it('does not carry filters into another establishment when the page stays mounted', () => {
    openSectionsFeed()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = (establishmentId: string) =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(TerrainTopbar, { variant: 'hub', pageTitle: 'Observations' }),
        createElement(SignalFeedPage, {
          onOpenSignal: vi.fn(),
          establishmentId,
        }),
      )

    const view = render(tree('est-1'))
    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))?.viewMode).toBe(
      'general',
    )

    feedQueryCalls.length = 0
    view.rerender(tree('est-2'))

    expect(screen.getByRole('tab', { name: 'Ma zone' }).getAttribute('aria-selected')).toBe('true')
    const establishmentCall = feedQueryCalls.find((call) => call[0] === 'est-2')
    expect(establishmentCall?.[1]).toBe('personal')
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))?.viewMode).toBe(
      'general',
    )
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-2'))?.viewMode).toBe(
      'personal',
    )
  })
})

describe('SignalFeedPage desktop actions', () => {
  beforeEach(() => {
    clearSignalFeedReadingMemory()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      variables: undefined,
    })
    openSectionsFeed()
  })

  afterEach(() => {
    cleanup()
    clearSignalFeedReadingMemory()
    vi.unstubAllEnvs()
  })

  it('opens an anchored menu without opening the detail on desktop web', () => {
    mockLgViewport(true)
    const onOpenSignal = vi.fn()
    renderSignalFeedPage({
      onOpenSignal,
      establishmentId: 'est-1',
    })

    const openControl = screen.getByRole('button', { name: /Signal ouvert/ })
    const actions = screen.getByRole('button', { name: "Actions de l'observation" })
    expect(openControl.contains(actions)).toBe(false)
    fireEvent.click(actions)
    expect(onOpenSignal).not.toHaveBeenCalled()
    expect(screen.getByRole('menu', { name: "Actions de l'observation" })).toBeTruthy()
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Nouvelle observation' })).toBeNull()
  })

  it('keeps the card and the actions sheet on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    mockLgViewport(true)
    const onOpenSignal = vi.fn()
    renderSignalFeedPage({ onOpenSignal, establishmentId: 'est-1' })

    const openControl = screen.getByRole('button', { name: /Signal ouvert/ })
    const actions = screen.getByRole('button', { name: "Actions de l'observation" })
    expect(openControl.contains(actions)).toBe(true)
    fireEvent.click(actions)
    expect(onOpenSignal).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog', { name: 'Actions' })).toBeTruthy()
    expect(screen.queryByRole('menu', { name: "Actions de l'observation" })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Nouvelle observation' })).toBeNull()
  })

  it('does not offer creation or card actions in Cross on desktop web', () => {
    mockLgViewport(true)
    renderSignalFeedPage({
      source: 'cross',
      establishmentId: null,
    })

    expect(screen.queryByRole('button', { name: 'Nouvelle observation' })).toBeNull()
    expect(screen.queryByRole('button', { name: "Actions de l'observation" })).toBeNull()
    expect(screen.queryByRole('tab', { name: 'Ma zone' })).toBeNull()
  })
})
