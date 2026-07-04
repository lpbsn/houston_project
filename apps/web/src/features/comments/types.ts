import type { components } from '@/api/generated/types'

export type CommentItem = components['schemas']['CommentItem']
export type CommentCreateRequest = components['schemas']['CommentCreateRequest']
export type CommentMention = components['schemas']['CommentMention']
export type MentionUserSearchResult = components['schemas']['ScopedUserSearchResult']
export type ExecutionCommentListItem = components['schemas']['ExecutionCommentListItem']
export type ExecutionCommentThreadItem = components['schemas']['ExecutionCommentThreadItem']
export type CommentPermissionHints = components['schemas']['CommentPermissionHints']

export function isExecutionThreadItem(
  item: ExecutionCommentListItem,
): item is ExecutionCommentListItem & { item_type: 'execution_thread' } {
  return item.item_type === 'execution_thread'
}

export function isExecutionInheritedSignalItem(
  item: ExecutionCommentListItem,
): item is ExecutionCommentListItem & { item_type: 'inherited_signal' } {
  return item.item_type === 'inherited_signal'
}
