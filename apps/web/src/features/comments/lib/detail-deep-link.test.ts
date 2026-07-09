import { describe, expect, it } from 'vitest'

import {
  buildCommentDeepLinkPath,
  buildExecutionValidationFocusPath,
  parseDetailDeepLink,
} from './detail-deep-link'

describe('detail deep link', () => {
  it('parses comments tab and comment id from search params', () => {
    expect(parseDetailDeepLink('?tab=comments&commentId=comment-1')).toEqual({
      tab: 'comments',
      commentId: 'comment-1',
      focus: null,
    })
  })

  it('parses validation focus from search params', () => {
    expect(parseDetailDeepLink('?focus=validation')).toEqual({
      tab: null,
      commentId: null,
      focus: 'validation',
    })
  })

  it('returns null values for unrelated search params', () => {
    expect(parseDetailDeepLink('?tab=details')).toEqual({
      tab: null,
      commentId: null,
      focus: null,
    })
    expect(parseDetailDeepLink('?focus=unknown')).toEqual({
      tab: null,
      commentId: null,
      focus: null,
    })
  })

  it('builds a comment deep link path', () => {
    expect(buildCommentDeepLinkPath('/signals/signal-1', 'comment-1')).toBe(
      '/signals/signal-1?tab=comments&commentId=comment-1',
    )
  })

  it('builds an execution validation focus path', () => {
    expect(buildExecutionValidationFocusPath('exec-1')).toBe(
      '/action-plans/executions/exec-1?focus=validation',
    )
  })
})
