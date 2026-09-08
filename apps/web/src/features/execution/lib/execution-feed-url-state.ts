import { todayCivilDate } from '@/lib/business-timezone'
import type { ExecutionViewMode } from '@/features/execution/lib/types'

export type ExecutionFeedLayout = 'list' | 'calendar'
export type ExecutionCalendarGranularity = 'day' | 'week' | 'month'

export type ExecutionFeedUrlState = {
  layout: ExecutionFeedLayout
  granularity: ExecutionCalendarGranularity
  anchor: string
  viewMode: ExecutionViewMode
}

const LAYOUTS = new Set<ExecutionFeedLayout>(['list', 'calendar'])
const GRANULARITIES = new Set<ExecutionCalendarGranularity>(['day', 'week', 'month'])
const VIEW_MODES = new Set<ExecutionViewMode>(['personal', 'general'])
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

function parseSearchParams(search: string): URLSearchParams {
  return new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
}

export function defaultExecutionFeedUrlState(now: Date = new Date()): ExecutionFeedUrlState {
  return {
    layout: 'list',
    granularity: 'week',
    anchor: todayCivilDate(undefined, now),
    viewMode: 'personal',
  }
}

export function parseExecutionFeedSearch(
  search: string,
  now: Date = new Date(),
): ExecutionFeedUrlState {
  const params = parseSearchParams(search)
  const defaults = defaultExecutionFeedUrlState(now)
  const layoutRaw = params.get('layout')
  const granularityRaw = params.get('granularity')
  const anchorRaw = params.get('anchor')
  const viewModeRaw = params.get('view_mode')
  return {
    layout: layoutRaw && LAYOUTS.has(layoutRaw as ExecutionFeedLayout)
      ? (layoutRaw as ExecutionFeedLayout)
      : defaults.layout,
    granularity:
      granularityRaw && GRANULARITIES.has(granularityRaw as ExecutionCalendarGranularity)
        ? (granularityRaw as ExecutionCalendarGranularity)
        : defaults.granularity,
    anchor: anchorRaw && ISO_DATE.test(anchorRaw) ? anchorRaw : defaults.anchor,
    viewMode:
      viewModeRaw && VIEW_MODES.has(viewModeRaw as ExecutionViewMode)
        ? (viewModeRaw as ExecutionViewMode)
        : defaults.viewMode,
  }
}

export function serializeExecutionFeedSearch(state: ExecutionFeedUrlState): string {
  const params = new URLSearchParams()
  if (state.layout !== 'list') {
    params.set('layout', state.layout)
  }
  if (state.layout === 'calendar') {
    params.set('granularity', state.granularity)
    params.set('anchor', state.anchor)
  }
  if (state.viewMode !== 'personal') {
    params.set('view_mode', state.viewMode)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function executionFeedHref(pathname: string, state: ExecutionFeedUrlState): string {
  return `${pathname}${serializeExecutionFeedSearch(state)}`
}

const FEED_SEARCH_KEYS = new Set(['layout', 'granularity', 'anchor', 'view_mode'])

export function appendExecutionFeedSearch(pathname: string, search: string): string {
  const incoming = parseSearchParams(search)
  const next = parseSearchParams(serializeExecutionFeedSearch(parseExecutionFeedSearch(search)))
  const incomingQuery = incoming.toString()
  if (incomingQuery) {
    for (const pair of incomingQuery.split('&')) {
      const separator = pair.indexOf('=')
      const rawKey = separator === -1 ? pair : pair.slice(0, separator)
      const key = decodeURIComponent(rawKey.replace(/\+/g, ' '))
      if (!key || FEED_SEARCH_KEYS.has(key)) {
        continue
      }
      const value = incoming.get(key)
      if (value != null) {
        next.set(key, value)
      }
    }
  }
  const query = next.toString()
  return query ? `${pathname}?${query}` : pathname
}
