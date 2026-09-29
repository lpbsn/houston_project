// @vitest-environment jsdom

import { createElement, useState } from 'react'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import type { SignalFeedItem } from '@/features/signals/types'
import {
  deferFeedListInvalidation,
  resetFeedReadingSessionsForTests,
} from '@/lib/feed-external-updates'

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
const openForSignalMock = vi.fn()
const runActionMock = vi.fn(() => 'close' as const)
const closeActionsMock = vi.fn()
const openActionsMock = vi.fn()

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
      items: [] as SignalFeedItem[],
      pins: [] as SignalFeedItem[],
      counts: { open: 0, in_progress: 0, interesting: 0, pinned: 0 },
      next_cursor: null,
      has_more: false,
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
  useLoadMoreSignalFeed: () => loadMoreMock(),
  useRefreshSignalFeed: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
  useResumeSignalFeed: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useLoadMoreCrossSignalFeedPins: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
}))

vi.mock('@/features/signals/hooks/use-signal-feed-quick-actions', () => ({
  useSignalFeedQuickActions: () => {
    const [activeItem, setActiveItem] = useState<FeedItemForActions | null>(null)
    const [actionsOpen, setActionsOpen] = useState(false)
    return {
      activeItem,
      actionsOpen,
      openActions: (item: FeedItemForActions) => {
        openActionsMock(item)
        setActiveItem(item)
        setActionsOpen(true)
      },
      closeActions: () => {
        closeActionsMock()
        setActionsOpen(false)
        setActiveItem(null)
      },
      runAction: (...args: unknown[]) => runActionMock(...args),
      isPending: false,
      actionError: null,
    }
  },
}))

vi.mock('@/features/signals/hooks/use-signal-qualify-sheet', () => ({
  useSignalQualifySheet: () => ({
    open: false,
    opening: false,
    signalId: null,
    signal: null,
    isPending: false,
    errorMessage: null,
    openForSignal: openForSignalMock,
    close: vi.fn(),
    submit: vi.fn(),
  }),
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
    onNavigate?: (pathname: string, options?: { replace?: boolean }) => void
    establishmentId?: string | null
    source?: 'establishment' | 'cross'
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  const tree = (
    nextProps: {
      onOpenSignal?: (signalId: string) => void
      onNavigate?: (pathname: string, options?: { replace?: boolean }) => void
      establishmentId?: string | null
      source?: 'establishment' | 'cross'
    } = props,
  ) =>
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(TerrainTopbar, { variant: 'hub', pageTitle: 'Observations' }),
      createElement(SignalFeedPage, {
        onOpenSignal: nextProps.onOpenSignal ?? vi.fn(),
        onNavigate: nextProps.onNavigate ?? vi.fn(),
        establishmentId: nextProps.establishmentId,
        source: nextProps.source,
      }),
    )
  const view = render(tree())
  return {
    ...view,
    rerenderPage: (
      nextProps: {
        onOpenSignal?: (signalId: string) => void
        onNavigate?: (pathname: string, options?: { replace?: boolean }) => void
        establishmentId?: string | null
        source?: 'establishment' | 'cross'
      } = props,
    ) => view.rerender(tree(nextProps)),
  }
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
        items: [
          buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' }),
          buildFeedItem({
            id: 'signal-progress',
            title: 'Signal en cours',
            status: 'in_progress',
          }),
        ],
        pins: [],
        counts: { open: 1, in_progress: 1, interesting: 0, pinned: 0 },
        next_cursor: null,
        has_more: false,
        applied_filters: {},
      },
    }),
  )
}

describe('SignalFeedPage separators', () => {
  beforeEach(() => {
    feedLoadMoreMutate.mockClear()
    feedQueryCalls.length = 0
    clearSignalFeedReadingMemory()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      isError: false,
      error: null,
    })
    feedQueryMock.mockReturnValue(buildFeedQueryState())
  })

  afterEach(() => {
    cleanup()
    resetFeedReadingSessionsForTests()
    clearSignalFeedReadingMemory()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
  })

  it('shows non-collapsible separators only for loaded categories', () => {
    openSectionsFeed()
    renderSignalFeedPage()

    expect(screen.getByText('Ouverts')).toBeTruthy()
    expect(screen.getAllByText('En cours').length).toBeGreaterThan(0)
    expect(screen.queryByText('Intéressants')).toBeNull()
    expect(screen.getByRole('heading', { level: 3, name: 'Signal ouvert' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Déplier la section/ })).toBeNull()
  })

  it('loads the next global page from one control', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [buildFeedItem({ id: 'signal-open', title: 'Signal ouvert', status: 'open' })],
          pins: [],
          counts: { open: 2, in_progress: 0, interesting: 0, pinned: 0 },
          next_cursor: 'cursor-2',
          has_more: true,
          applied_filters: {},
        },
      }),
    )

    renderSignalFeedPage()

    fireEvent.click(screen.getByRole('button', { name: 'Charger la suite' }))
    expect(feedLoadMoreMutate).toHaveBeenCalledTimes(1)
    expect(feedLoadMoreMutate.mock.calls[0]).toEqual([])
  })

  it('keeps a zero interesting filter available and shows counts independent of the selection', () => {
    openSectionsFeed()
    renderSignalFeedPage()

    const interesting = screen.getByRole('button', { name: 'Intéressants · 0' })
    expect(interesting.hasAttribute('disabled')).toBe(false)
    expect(screen.getByRole('button', { name: 'Ouverts · 1' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tout · 2' })).toBeTruthy()

    fireEvent.click(interesting)

    expect(screen.getByRole('button', { name: 'Tout' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Tout · 2' })).toBeNull()
    expect(feedQueryCalls.at(-1)?.[2]).toMatchObject({ statuses: ['interesting'] })
  })

  it('shows pinned cards and a local empty list when only pins are loaded', () => {
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [],
          pins: [
            buildFeedItem({
              id: 'pinned-open',
              title: 'Épinglée ouverte',
              status: 'open',
              is_pinned: true,
            }),
          ],
          counts: { open: 0, in_progress: 0, interesting: 0, pinned: 1 },
          next_cursor: null,
          has_more: false,
          applied_filters: {},
        },
      }),
    )

    renderSignalFeedPage()

    expect(screen.getByRole('heading', { level: 3, name: 'Épinglée ouverte' })).toBeTruthy()
    expect(screen.getByTestId('signal-feed-pinned-carousel')).toBeTruthy()
    expect(screen.getByText('Aucune autre observation')).toBeTruthy()
    expect(screen.queryByText('Aucune observation active')).toBeNull()
  })
})

describe('SignalFeedPage reading restoration', () => {
  beforeEach(() => {
    feedQueryCalls.length = 0
    clearSignalFeedReadingMemory()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      isError: false,
      error: null,
    })
    openSectionsFeed()
  })

  afterEach(() => {
    cleanup()
    resetFeedReadingSessionsForTests()
    clearSignalFeedReadingMemory()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
  })

  it('restores view, filters, open section and scroll after an internal remount of the same scope', () => {
    const scopeKey = signalFeedReadingScopeKey('establishment', 'est-1')
    renderSignalFeedPage()
    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    const scroller = screen.getByTestId('signal-feed-scroll')
    scroller.scrollTop = 140
    fireEvent.scroll(scroller)

    expect(readSignalFeedReading(scopeKey)?.viewMode).toBe('general')
    expect(readSignalFeedReading(scopeKey)?.scrollTop).toBe(140)

    cleanup()
    renderSignalFeedPage()

    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
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
      scrollTop: 90,
    })

    renderSignalFeedPage({ establishmentId: 'est-2' })

    expect(screen.getByRole('tab', { name: 'Ma zone' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
    const establishmentCall = feedQueryCalls.find((call) => call[0] === 'est-2')
    expect(establishmentCall?.[1]).toBe('personal')
    expect(establishmentCall?.[2]).toMatchObject({ statuses: [] })
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(0)
  })

  it('keeps reading state per establishment across A → B → A without unmounting', () => {
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
          onNavigate: vi.fn(),
          establishmentId,
        }),
      )

    const view = render(tree('est-1'))
    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    const scrollerA = screen.getByTestId('signal-feed-scroll')
    scrollerA.scrollTop = 140
    fireEvent.scroll(scrollerA)

    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))).toMatchObject({
      viewMode: 'general',
      scrollTop: 140,
    })

    feedQueryCalls.length = 0
    view.rerender(tree('est-2'))

    expect(screen.getByRole('tab', { name: 'Ma zone' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(0)
    const establishmentBCall = feedQueryCalls.find((call) => call[0] === 'est-2')
    expect(establishmentBCall?.[1]).toBe('personal')
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))).toMatchObject({
      viewMode: 'general',
      scrollTop: 140,
    })
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-2'))?.viewMode).toBe(
      'personal',
    )

    feedQueryCalls.length = 0
    view.rerender(tree('est-1'))

    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByRole('heading', { level: 3, name: 'Signal en cours' })).toBeTruthy()
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(140)
    const establishmentACall = feedQueryCalls.find((call) => call[0] === 'est-1')
    expect(establishmentACall?.[1]).toBe('general')
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))).toMatchObject({
      viewMode: 'general',
      scrollTop: 140,
    })
  })

  it('defers invalidation at scrollTop zero when page one is not displayed', () => {
    const focusedItem = buildFeedItem({ id: 'focused', title: 'Fenêtre évincée' })
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [focusedItem],
          pins: [],
          counts: { open: 2, in_progress: 0, interesting: 0, pinned: 0 },
          next_cursor: null,
          has_more: false,
          applied_filters: {},
          readingWindow: {
            generation: 1,
            pageOne: {
              requestCursor: null,
              nextCursor: 'cursor-1',
              hasMore: true,
              items: [buildFeedItem({ id: 'page-one' })],
            },
            focus: [
              {
                requestCursor: 'cursor-2',
                nextCursor: null,
                hasMore: false,
                items: [focusedItem],
              },
            ],
            behindCursor: 'cursor-1',
            stalled: false,
          },
          pinWindow: {
            generation: 1,
            pageOne: {
              requestCursor: null,
              nextCursor: null,
              hasMore: false,
              items: [],
            },
            focus: [],
            behindCursor: null,
            stalled: false,
          },
        },
      }),
    )
    renderSignalFeedPage()

    let deferred = false
    act(() => {
      deferred = deferFeedListInvalidation(['signals', 'feed', 'est-1', 'personal'])
    })

    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(0)
    expect(deferred).toBe(true)
    expect(screen.getByText('Mises à jour disponibles')).toBeTruthy()
  })

  it('publishes the restored scroll edge when content arrives after mount', () => {
    writeSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'), {
      scrollTop: 140,
    })
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        isLoading: true,
        isSuccess: false,
        data: undefined,
      }),
    )
    const view = renderSignalFeedPage()
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(0)

    openSectionsFeed()
    view.rerenderPage()

    let deferred = false
    act(() => {
      deferred = deferFeedListInvalidation(['signals', 'feed', 'est-1', 'personal'])
    })
    expect(screen.getByTestId('signal-feed-scroll').scrollTop).toBe(140)
    expect(deferred).toBe(true)
  })

  it('stores and restores an anchor from the pinned collection', () => {
    const pinned = buildFeedItem({
      id: 'pinned-anchor',
      title: 'Épingle ancrée',
      is_pinned: true,
    })
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [],
          pins: [pinned],
          counts: { open: 0, in_progress: 0, interesting: 0, pinned: 1 },
          next_cursor: null,
          has_more: false,
          applied_filters: {},
        },
      }),
    )
    const onOpenSignal = vi.fn()
    renderSignalFeedPage({ onOpenSignal })
    fireEvent.click(screen.getByRole('button', { name: /Épingle ancrée/ }))

    expect(onOpenSignal).toHaveBeenCalledWith('pinned-anchor')
    expect(
      readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))?.anchorId,
    ).toBe('pinned-anchor')

    cleanup()
    const scrollIntoView = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoView
    renderSignalFeedPage({ onOpenSignal })
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'center' })
    Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
  })
})

describe('SignalFeedPage desktop actions', () => {
  beforeEach(() => {
    clearSignalFeedReadingMemory()
    openForSignalMock.mockReset()
    openForSignalMock.mockResolvedValue({ ok: true })
    runActionMock.mockClear()
    closeActionsMock.mockClear()
    openActionsMock.mockClear()
    loadMoreMock.mockReturnValue({
      mutate: feedLoadMoreMutate,
      isPending: false,
      isError: false,
      error: null,
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
    const openRow = openControl.closest('article')
    const actions = within(openRow as HTMLElement).getByRole('button', {
      name: "Actions de l'observation",
    })
    expect(openControl.contains(actions)).toBe(false)
    fireEvent.click(actions)
    expect(onOpenSignal).not.toHaveBeenCalled()
    expect(screen.getByRole('menu', { name: "Actions de l'observation" })).toBeTruthy()
    expect(screen.queryByRole('dialog', { name: 'Actions' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Nouvelle observation' })).toBeNull()
  })

  it('routes qualify to openForSignal and pin to runAction on desktop', () => {
    mockLgViewport(true)
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [
            buildFeedItem({
              id: 'signal-open',
              title: 'Signal ouvert',
              status: 'open',
              permission_hints: {
                ...buildFeedItem().permission_hints,
                can_pin: true,
                can_qualify_routing: true,
                can_cancel: false,
                can_resolve: false,
              },
            }),
          ],
          pins: [],
          next_cursor: null,
          has_more: false,
        },
      }),
    )
    renderSignalFeedPage({ establishmentId: 'est-1' })

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Qualifier' }))
    expect(openForSignalMock).toHaveBeenCalledWith('signal-open')
    expect(runActionMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    expect(runActionMock).toHaveBeenCalledWith('pin', expect.objectContaining({ id: 'signal-open' }))
  })

  it('keeps the card and the actions sheet on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    mockLgViewport(true)
    const onOpenSignal = vi.fn()
    renderSignalFeedPage({ onOpenSignal, establishmentId: 'est-1' })

    const openControl = screen.getByRole('button', { name: /Signal ouvert/ })
    const openRow = openControl.closest('article')
    const actions = within(openRow as HTMLElement).getByRole('button', {
      name: "Actions de l'observation",
    })
    expect(openControl.contains(actions)).toBe(true)
    fireEvent.click(actions)
    expect(onOpenSignal).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog', { name: 'Actions' })).toBeTruthy()
    expect(screen.queryByRole('menu', { name: "Actions de l'observation" })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Nouvelle observation' })).toBeNull()
  })

  it('routes qualify to openForSignal from the mobile actions sheet', () => {
    mockLgViewport(false)
    feedQueryMock.mockReturnValue(
      buildFeedQueryState({
        data: {
          items: [
            buildFeedItem({
              id: 'signal-open',
              title: 'Signal ouvert',
              status: 'open',
              permission_hints: {
                ...buildFeedItem().permission_hints,
                can_pin: true,
                can_qualify_routing: true,
                can_cancel: false,
                can_resolve: false,
              },
            }),
          ],
          pins: [],
          next_cursor: null,
          has_more: false,
        },
      }),
    )
    renderSignalFeedPage({ establishmentId: 'est-1' })

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))
    expect(screen.getByRole('dialog', { name: 'Actions' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Qualifier' }))
    expect(openForSignalMock).toHaveBeenCalledWith('signal-open')
    expect(runActionMock).not.toHaveBeenCalled()
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
