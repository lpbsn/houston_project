import type { CommentAttachment, ExecutionCommentListItem } from '../types'
import { isExecutionThreadItem } from '../types'

export function flattenAvailablePlanAttachments(
  comments: ExecutionCommentListItem[] | undefined,
): CommentAttachment[] {
  if (!comments) {
    return []
  }
  const attachments: CommentAttachment[] = []
  for (const item of comments) {
    if (!isExecutionThreadItem(item)) {
      continue
    }
    attachments.push(...(item.attachments ?? []))
    for (const reply of item.replies ?? []) {
      attachments.push(...(reply.attachments ?? []))
    }
  }
  return attachments
}
