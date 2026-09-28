import { writeFileSync } from 'node:fs'

import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { actionPlansQueryKeys } from '@/features/action-plans/api'
import {
  appendExecutionFeedWindow,
  executionFeedCacheFromPage,
} from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedItemWrapper,
  ActionPlanExecutionFeedResponse,
} from '@/features/action-plans/types'
import { signalsQueryKeys } from '@/features/signals/api'
import {
  appendSignalFeedPage,
  signalFeedCacheFromFirstPage,
} from '@/features/signals/lib/signal-feed-cache'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  type SignalFeedFilters,
} from '@/features/signals/lib/signal-feed-filters'
import type {
  SignalFeedItem,
  SignalFeedResponse,
  SignalViewMode,
} from '@/features/signals/types'
import {
  FEED_FOCUS_PAGE_LIMIT,
  hydratedItems,
  renderedItems,
} from '@/lib/feed-reading-window'
import {
  invalidateActionPlanExecutionFeedQueries,
  invalidateEstablishmentSignalQueries,
} from '@/lib/query-invalidation'

const REFERENCE_COMMIT =
  process.env.FEED_BASELINE_REFERENCE_COMMIT ?? 'unknown-reference-commit'
const PAGE_SIZE = 25
const SESSION_PAGES = 20

function signalItem(id: string): SignalFeedItem {
  return {
    id,
    title: id,
    structured_summary_short: 'Synthetic signal used only for cache measurement.',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: false,
    affected_business_unit_id: null,
    affected_business_unit_key: 'operations',
    affected_business_unit_label: 'Operations',
    responsible_business_unit_id: null,
    responsible_business_unit_key: 'operations',
    responsible_business_unit_label: 'Operations',
    activity_subject_id: null,
    activity_subject_normalized_name: 'feed baseline',
    activity_subject_label: 'Feed baseline',
    operational_unit_key: null,
    location_text: 'Zone baseline',
    media_count: 0,
    last_activity_at: '2026-09-28T12:00:00Z',
    created_at: '2026-09-28T11:00:00Z',
    reporter_display_name: 'Baseline User',
    aggregation_count: 2,
    permission_hints: {
      can_pin: true,
      can_mark_interesting: true,
      can_cancel: true,
      can_resolve: true,
      can_create_linked_action_plan: true,
      can_qualify_routing: false,
      can_request_resolution: true,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
    },
    resolution_request: null,
  } satisfies SignalFeedItem
}

function signalPage(page: number): SignalFeedResponse {
  const hasMore = page < SESSION_PAGES - 1
  return {
    items: Array.from({ length: PAGE_SIZE }, (_, index) =>
      signalItem(`signal-${page * PAGE_SIZE + index}`),
    ),
    pins: page === 0 ? [signalItem('signal-pin-1'), signalItem('signal-pin-2')] : undefined,
    counts:
      page === 0
        ? { open: SESSION_PAGES * PAGE_SIZE, in_progress: 0, interesting: 0, pinned: 2 }
        : undefined,
    applied_filters:
      page === 0
        ? {
            view_mode: 'general',
            statuses: [],
            business_unit_ids: [],
            activity_subject_ids: [],
            needs_qualification: false,
          }
        : undefined,
    next_cursor: hasMore ? `signal-cursor-${page + 1}` : null,
    has_more: hasMore,
    pins_next_cursor: null,
    pins_has_more: false,
  } as SignalFeedResponse
}

function executionItem(id: string): ActionPlanExecutionFeedItemWrapper {
  return {
    item_type: 'action_plan_execution',
    action_plan_execution: {
      id,
      title: id,
      description_short: 'Synthetic execution used only for cache measurement.',
      status: 'in_progress',
      requires_validation: true,
      validated_at: null,
      validated_by_display_name: null,
      pilot_business_unit: {
        id: 'bu-baseline',
        specific_name: 'Operations',
        instance_description: '',
        active: true,
        generic: {
          key: 'operations',
          label: 'Operations',
          description: '',
          unit_type: 'dedicated',
        },
      },
      signal_summary: null,
      start_at: '2026-09-28T08:00:00Z',
      end_at: '2026-09-29T18:00:00Z',
      all_day: false,
      visible_from: '2026-09-27T07:00:00Z',
      is_overdue: false,
      task_count: 3,
      treated_task_count: 0,
      task_executions: [],
      last_activity_at: '2026-09-28T12:00:00Z',
      created_at: '2026-09-28T11:00:00Z',
      created_by_display_name: 'Baseline User',
      marked_done_at: null,
      marked_done_by_display_name: null,
      canceled_at: null,
      active_review: null,
      assignees: [],
      involved_poles: [],
      is_pinned: false,
      permission_hints: {
        can_pin: true,
        can_mark_done: true,
        can_validate: true,
        can_reopen: false,
        can_cancel: true,
        can_update: true,
        is_pilot_pole_assignee: true,
      },
    } satisfies ActionPlanExecutionFeedItem,
  }
}

function executionPage(page: number): ActionPlanExecutionFeedResponse {
  const hasMore = page < SESSION_PAGES - 1
  return {
    items: Array.from({ length: PAGE_SIZE }, (_, index) =>
      executionItem(`execution-${page * PAGE_SIZE + index}`),
    ),
    pins: page === 0 ? [executionItem('execution-pin-1')] : undefined,
    section_counts:
      page === 0
        ? { pinned: 1, pending_validation: 100, overdue: 100, in_progress: 300 }
        : undefined,
    scheduled: page === 0 ? { count: 20, next: null } : undefined,
    next_cursor: hasMore ? `execution-cursor-${page + 1}` : null,
    has_more: hasMore,
  } as ActionPlanExecutionFeedResponse
}

function simulateSignalSession() {
  let cache = signalFeedCacheFromFirstPage(signalPage(0))
  for (let page = 1; page < SESSION_PAGES; page += 1) {
    const appended = appendSignalFeedPage(
      cache,
      signalPage(page),
      `signal-cursor-${page}`,
    )
    cache = appended.feed
  }
  return cache
}

function simulateExecutionSession() {
  let cache = executionFeedCacheFromPage(executionPage(0))
  for (let page = 1; page < SESSION_PAGES; page += 1) {
    cache = {
      ...cache,
      window: appendExecutionFeedWindow(
        cache.window,
        executionPage(page),
        `execution-cursor-${page}`,
      ).window,
    }
  }
  return cache
}

function invalidationCounts() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const spy = vi.spyOn(queryClient, 'invalidateQueries')
  invalidateEstablishmentSignalQueries(queryClient, 'est-1', { force: true })
  const signal = spy.mock.calls.map(([filters]) => filters.queryKey ?? ['predicate'])
  spy.mockClear()
  invalidateActionPlanExecutionFeedQueries(queryClient, 'est-1', { force: true })
  const execution = spy.mock.calls.map(([filters]) => filters.queryKey ?? ['predicate'])
  spy.mockRestore()
  queryClient.clear()
  return { signal, execution }
}

function queryCacheSnapshot(signalCache: unknown, executionCache: unknown) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  const statuses: SignalFeedFilters['statuses'][] = [
    [],
    ['open'],
    ['in_progress'],
    ['interesting'],
  ]
  for (const viewMode of ['personal', 'general'] satisfies SignalViewMode[]) {
    for (const statusSelection of statuses) {
      queryClient.setQueryData(
        signalsQueryKeys.feed('est-1', viewMode, {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          statuses: statusSelection,
        }),
        signalCache,
      )
    }
  }
  for (const viewMode of ['personal', 'general'] as const) {
    for (const category of ['all', 'pending_validation', 'overdue', 'in_progress'] as const) {
      queryClient.setQueryData(
        actionPlansQueryKeys.executionFeed('est-1', viewMode, category),
        executionCache,
      )
    }
  }
  const queries = queryClient.getQueryCache().getAll()
  const snapshot = {
    total_entries: queries.length,
    signal_entries: queries.filter((query) => query.queryKey[0] === 'signals').length,
    execution_entries: queries.filter((query) => query.queryKey[0] === 'action-plans')
      .length,
    serialized_cache_bytes: Buffer.byteLength(
      JSON.stringify(queries.map((query) => query.state.data)),
    ),
  }
  queryClient.clear()
  return snapshot
}

describe('post-Lots 0-7 feed hardening baseline', () => {
  it('captures bounded-window, cache duplication, and invalidation metrics', () => {
    const signalCache = simulateSignalSession()
    const executionCache = simulateExecutionSession()
    const signalHydrated = hydratedItems(signalCache.readingWindow)
    const signalRendered = renderedItems(signalCache.readingWindow, (item) => item.id)
    const executionHydrated = hydratedItems(executionCache.window)
    const executionRendered = renderedItems(
      executionCache.window,
      (item) => item.action_plan_execution.id,
    )
    const invalidations = invalidationCounts()

    const report = {
      schema_version: 'feed_frontend_baseline_v2',
      reference_commit: REFERENCE_COMMIT,
      runtime: {
        node: process.version,
        platform: process.platform,
        page_size: PAGE_SIZE,
        simulated_pages: SESSION_PAGES,
      },
      signal_window: {
        focus_page_limit: FEED_FOCUS_PAGE_LIMIT,
        focus_pages: signalCache.readingWindow.focus.length,
        hydrated_items: signalHydrated.length,
        rendered_items: signalRendered.length,
        projected_items: signalCache.items.length,
        retained_page_one_items: signalCache.readingWindow.pageOne?.items.length ?? 0,
        duplicate_projected_references: signalCache.items.length,
        serialized_state_bytes: Buffer.byteLength(JSON.stringify(signalCache)),
      },
      execution_window: {
        focus_page_limit: FEED_FOCUS_PAGE_LIMIT,
        focus_pages: executionCache.window.focus.length,
        hydrated_items: executionHydrated.length,
        rendered_items: executionRendered.length,
        retained_page_one_items: executionCache.window.pageOne?.items.length ?? 0,
        serialized_state_bytes: Buffer.byteLength(JSON.stringify(executionCache)),
      },
      query_cache: queryCacheSnapshot(signalCache, executionCache),
      invalidation_fanout: {
        signal_call_count: invalidations.signal.length,
        signal_query_keys: invalidations.signal,
        execution_call_count: invalidations.execution.length,
        execution_query_keys: invalidations.execution,
      },
      browser_metrics: {
        status: 'manual_protocol_required',
        reason:
          'React commit duration and JavaScript heap are not comparable under Vitest/jsdom.',
      },
    }

    expect(signalCache.readingWindow.focus.length).toBeLessThanOrEqual(
      FEED_FOCUS_PAGE_LIMIT,
    )
    expect(executionCache.window.focus.length).toBeLessThanOrEqual(
      FEED_FOCUS_PAGE_LIMIT,
    )
    expect(report.query_cache.total_entries).toBe(16)

    const serialized = JSON.stringify(report, null, 2)
    if (process.env.FEED_BASELINE_OUTPUT) {
      writeFileSync(process.env.FEED_BASELINE_OUTPUT, `${serialized}\n`, 'utf8')
    }
    console.info(`FEED_BASELINE_JSON:${JSON.stringify(report)}`)
  })
})
