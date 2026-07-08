import { describe, expect, it } from 'vitest'

import {
  buildCommentDeepLinkPath,
  parseDetailDeepLink,
} from './detail-deep-link'

describe('detail deep link', () => {
  it('parses comments tab and comment id from search params', () => {
    expect(parseDetailDeepLink('?tab=comments&commentId=comment-1')).toEqual({
      tab: 'comments',
      commentId: 'comment-1',
    })
  })

  it('returns null values for unrelated search params', () => {
    expect(parseDetailDeepLink('?tab=details')).toEqual({
      tab: null,
      commentId: null,
    })
  })

  it('builds a comment deep link path', () => {
    expect(buildCommentDeepLinkPath('/signals/signal-1', 'comment-1')).toBe(
      '/signals/signal-1?tab=comments&commentId=comment-1',
    )
  })
})
