import { describe, expect, it } from 'vitest'

import { flattenAvailablePlanAttachments } from './flatten-plan-attachments'
import type { ExecutionCommentListItem } from '../types'

function attachment(id: string, commentId: string) {
  return {
    id,
    kind: 'image' as const,
    content_type: 'image/png',
    size_bytes: 12,
    original_filename: `${id}.png`,
    preview_url: `/preview/${id}`,
    thumbnail_url: null,
    comment_id: commentId,
    created_at: '2026-09-21T10:00:00Z',
    author_display_name: 'Alice',
  }
}

describe('flattenAvailablePlanAttachments', () => {
  it('collects root and reply attachments and ignores inherited signal comments', () => {
    const comments = [
      {
        item_type: 'inherited_signal',
        id: 'sig-1',
        origin: 'signal',
        body: 'signal',
        author: { membership_id: 'm-1', display_name: 'Alice' },
        mentions: [],
        created_at: '2026-09-21T09:00:00Z',
      },
      {
        item_type: 'execution_thread',
        id: 'root-1',
        origin: 'action_plan_execution',
        body: 'root',
        author: { membership_id: 'm-1', display_name: 'Alice' },
        mentions: [],
        created_at: '2026-09-21T10:00:00Z',
        attachments: [attachment('a1', 'root-1')],
        replies: [
          {
            id: 'reply-1',
            origin: 'action_plan_execution',
            body: 'reply',
            author: { membership_id: 'm-1', display_name: 'Alice' },
            mentions: [],
            created_at: '2026-09-21T10:05:00Z',
            attachments: [attachment('a2', 'reply-1')],
          },
        ],
        is_resolved: false,
        resolved_at: null,
        resolved_by: null,
        permission_hints: { can_reply: true, can_resolve: true },
      },
    ] as ExecutionCommentListItem[]

    expect(flattenAvailablePlanAttachments(comments).map((item) => item.id)).toEqual(['a1', 'a2'])
  })
})
