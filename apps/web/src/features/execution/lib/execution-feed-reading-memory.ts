import type {
  ActionPlanExecutionFeedCategory,
  ActionPlanExecutionFeedViewMode,
} from '@/features/action-plans/api'

export type ExecutionFeedReadingState = {
  viewMode: ActionPlanExecutionFeedViewMode
  category: ActionPlanExecutionFeedCategory
  expandedByKey: Record<string, boolean>
  scrollTop: number
  anchorId: string | null
  neighborId: string | null
  resumeCursor: string | null
  authorizationFingerprint: string | null
}

const memory = new Map<string, ExecutionFeedReadingState>()

export function executionFeedReadingScopeKey(
  source: 'establishment' | 'cross',
  establishmentId: string | null,
): string {
  if (source === 'cross') {
    return 'cross'
  }
  return `establishment:${establishmentId ?? 'unknown'}`
}

export function readExecutionFeedReading(scopeKey: string): ExecutionFeedReadingState | null {
  return memory.get(scopeKey) ?? null
}

export function writeExecutionFeedReading(
  scopeKey: string,
  patch: Partial<ExecutionFeedReadingState> &
    Pick<ExecutionFeedReadingState, 'category' | 'viewMode'>,
): void {
  const current = memory.get(scopeKey)
  memory.set(scopeKey, {
    viewMode: patch.viewMode,
    category: patch.category,
    expandedByKey: patch.expandedByKey ?? current?.expandedByKey ?? {},
    scrollTop: patch.scrollTop ?? current?.scrollTop ?? 0,
    anchorId: patch.anchorId === undefined ? (current?.anchorId ?? null) : patch.anchorId,
    neighborId: patch.neighborId === undefined ? (current?.neighborId ?? null) : patch.neighborId,
    resumeCursor:
      patch.resumeCursor === undefined ? (current?.resumeCursor ?? null) : patch.resumeCursor,
    authorizationFingerprint:
      patch.authorizationFingerprint === undefined
        ? (current?.authorizationFingerprint ?? null)
        : patch.authorizationFingerprint,
  })
}

export function clearExecutionFeedReadingMemory(): void {
  memory.clear()
}
