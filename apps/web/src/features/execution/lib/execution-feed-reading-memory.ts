import type {
  ActionPlanExecutionFeedCategory,
  ActionPlanExecutionFeedViewMode,
} from '@/features/action-plans/api'

export type ExecutionFeedReadingState = {
  viewMode: ActionPlanExecutionFeedViewMode
  category: ActionPlanExecutionFeedCategory
  expandedByKey: Record<string, boolean>
  scrollTop: number
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
  })
}

export function clearExecutionFeedReadingMemory(): void {
  memory.clear()
}
