import { describe, expect, it } from 'vitest'

import type { ExecutionCommentListItem } from '../types'
import { commentMatchesDiscussionFilter } from './discussion-filter'

function thread(
  overrides: Partial<ExecutionCommentListItem> = {},
): ExecutionCommentListItem {
  return {
    item_type: 'execution_thread',
    id: 'thread-1',
    origin: 'action_plan_execution',
    body: 'note',
    author: { membership_id: 'm-1', display_name: 'Alice' },
    mentions: [],
    created_at: '2026-06-15T10:00:00Z',
    replies: [],
    is_resolved: false,
    ...overrides,
  }
}

describe('commentMatchesDiscussionFilter', () => {
  it('keeps every comment when the filter is all', () => {
    expect(commentMatchesDiscussionFilter(thread({ is_resolved: true }), 'all')).toBe(true)
    expect(
      commentMatchesDiscussionFilter(
        thread({ item_type: 'inherited_signal', id: 'signal-1' }),
        'all',
      ),
    ).toBe(true)
  })

  it('keeps unresolved execution threads and hides resolved ones', () => {
    expect(commentMatchesDiscussionFilter(thread(), 'unresolved')).toBe(true)
    expect(commentMatchesDiscussionFilter(thread({ is_resolved: true }), 'unresolved')).toBe(false)
    expect(
      commentMatchesDiscussionFilter(
        thread({ item_type: 'inherited_signal', id: 'signal-1', is_resolved: false }),
        'unresolved',
      ),
    ).toBe(false)
  })

  it('keeps a highlighted comment even when the unresolved filter would hide it', () => {
    const resolved = thread({
      id: 'resolved-1',
      is_resolved: true,
      replies: [
        {
          id: 'reply-1',
          origin: 'action_plan_execution',
          body: 'suite',
          author: { membership_id: 'm-2', display_name: 'Bob' },
          mentions: [],
          created_at: '2026-06-15T11:00:00Z',
        },
      ],
    })

    expect(commentMatchesDiscussionFilter(resolved, 'unresolved', 'resolved-1')).toBe(true)
    expect(commentMatchesDiscussionFilter(resolved, 'unresolved', 'reply-1')).toBe(true)
    expect(commentMatchesDiscussionFilter(resolved, 'unresolved', 'other')).toBe(false)
  })

  it('keeps pinned decisions and a highlighted comment outside that set', () => {
    const pinned = thread({ id: 'pinned-1', pinned: true, is_resolved: true })
    const plain = thread({ id: 'plain-1', pinned: false })

    expect(commentMatchesDiscussionFilter(pinned, 'pinned')).toBe(true)
    expect(commentMatchesDiscussionFilter(plain, 'pinned')).toBe(false)
    expect(commentMatchesDiscussionFilter(plain, 'pinned', 'plain-1')).toBe(true)
  })
})
