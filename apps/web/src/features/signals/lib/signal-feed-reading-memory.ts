import {
  EMPTY_SIGNAL_FEED_FILTERS,
  normalizeSignalFeedFilters,
  type SignalFeedFilters,
} from './signal-feed-filters'
import type { SignalViewMode } from '../types'

export type SignalFeedReadingState = {
  viewMode: SignalViewMode
  filters: SignalFeedFilters
  expandedByKey: Record<string, boolean>
  scrollTop: number
  anchorId: string | null
  neighborId: string | null
  resumeCursor: string | null
  authorizationFingerprint: string | null
}

const memory = new Map<string, SignalFeedReadingState>()

export function signalFeedReadingScopeKey(
  source: 'establishment' | 'cross',
  establishmentId: string | null,
): string {
  if (source === 'cross') {
    return 'cross'
  }
  return `establishment:${establishmentId ?? 'unknown'}`
}

function emptyReadingState(): SignalFeedReadingState {
  return {
    viewMode: 'personal',
    filters: EMPTY_SIGNAL_FEED_FILTERS,
    expandedByKey: {},
    scrollTop: 0,
    anchorId: null,
    neighborId: null,
    resumeCursor: null,
    authorizationFingerprint: null,
  }
}

export function readSignalFeedReading(scopeKey: string): SignalFeedReadingState | null {
  return memory.get(scopeKey) ?? null
}

export function writeSignalFeedReading(
  scopeKey: string,
  patch: Partial<SignalFeedReadingState>,
): void {
  const current = memory.get(scopeKey) ?? emptyReadingState()
  memory.set(scopeKey, {
    viewMode: patch.viewMode ?? current.viewMode,
    filters: patch.filters ? normalizeSignalFeedFilters(patch.filters) : current.filters,
    expandedByKey: patch.expandedByKey ?? current.expandedByKey,
    scrollTop: patch.scrollTop ?? current.scrollTop,
    anchorId: patch.anchorId === undefined ? current.anchorId : patch.anchorId,
    neighborId: patch.neighborId === undefined ? current.neighborId : patch.neighborId,
    resumeCursor: patch.resumeCursor === undefined ? current.resumeCursor : patch.resumeCursor,
    authorizationFingerprint:
      patch.authorizationFingerprint === undefined
        ? current.authorizationFingerprint
        : patch.authorizationFingerprint,
  })
}

export function clearSignalFeedReadingMemory(): void {
  memory.clear()
}
