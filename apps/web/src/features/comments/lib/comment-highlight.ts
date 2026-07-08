import type { CommentItem, ExecutionCommentListItem } from '../types'
import { isExecutionInheritedSignalItem, isExecutionThreadItem } from '../types'

export const COMMENT_DOM_ID_PREFIX = 'comment-'
export const COMMENT_SCROLL_ANCHOR_CLASS = 'scroll-mt-16'
export const SCROLL_RETRY_MAX_ATTEMPTS = 10

export function commentDomId(commentId: string): string {
  return `${COMMENT_DOM_ID_PREFIX}${commentId}`
}

export function commentExistsInSignalList(
  comments: CommentItem[],
  commentId: string,
): boolean {
  return comments.some((comment) => comment.id === commentId)
}

export function commentExistsInExecutionList(
  comments: ExecutionCommentListItem[],
  commentId: string,
): boolean {
  for (const item of comments) {
    if (item.id === commentId) {
      return true
    }
    if (isExecutionThreadItem(item)) {
      if (item.replies?.some((reply) => reply.id === commentId)) {
        return true
      }
    }
    if (isExecutionInheritedSignalItem(item) && item.id === commentId) {
      return true
    }
  }
  return false
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function scrollToHighlightedComment(commentId: string): () => void {
  let cancelled = false
  let attempt = 0
  let rafId: number | null = null

  const cancel = () => {
    cancelled = true
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
    }
  }

  const tryScroll = () => {
    if (cancelled) {
      return
    }

    const element = document.getElementById(commentDomId(commentId))
    if (element) {
      element.scrollIntoView({
        block: 'center',
        behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      })
      return
    }

    attempt += 1
    if (attempt >= SCROLL_RETRY_MAX_ATTEMPTS) {
      return
    }

    rafId = requestAnimationFrame(tryScroll)
  }

  rafId = requestAnimationFrame(tryScroll)
  return cancel
}
