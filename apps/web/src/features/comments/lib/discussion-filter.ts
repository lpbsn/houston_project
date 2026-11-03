import type { ExecutionCommentListItem } from '../types'

export type DiscussionListFilter = 'all' | 'unresolved' | 'pinned'

export function commentMatchesDiscussionFilter(
  item: ExecutionCommentListItem,
  filter: DiscussionListFilter,
  highlightCommentId?: string | null,
): boolean {
  if (filter === 'all') {
    return true
  }
  if (
    highlightCommentId != null &&
    (item.id === highlightCommentId ||
      item.replies?.some((reply) => reply.id === highlightCommentId))
  ) {
    return true
  }
  if (filter === 'pinned') {
    return item.pinned === true
  }
  return item.item_type === 'execution_thread' && item.is_resolved !== true
}
