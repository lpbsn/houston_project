export { useLocationSearch } from '@/lib/location-search'

export const COMMENT_DEEP_LINK_TAB = 'comments'
export const COMMENT_DEEP_LINK_COMMENT_ID_PARAM = 'commentId'
export const EXECUTION_VALIDATION_FOCUS = 'validation'
export const EXECUTION_VALIDATION_FOCUS_PARAM = 'focus'

export type DetailDeepLink = {
  tab: typeof COMMENT_DEEP_LINK_TAB | null
  commentId: string | null
  focus: typeof EXECUTION_VALIDATION_FOCUS | null
}

export function parseDetailDeepLink(search: string): DetailDeepLink {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const tab = params.get('tab')
  const commentId = params.get(COMMENT_DEEP_LINK_COMMENT_ID_PARAM)?.trim() ?? null
  const focus = params.get(EXECUTION_VALIDATION_FOCUS_PARAM)

  return {
    tab: tab === COMMENT_DEEP_LINK_TAB ? COMMENT_DEEP_LINK_TAB : null,
    commentId: commentId && commentId.length > 0 ? commentId : null,
    focus: focus === EXECUTION_VALIDATION_FOCUS ? EXECUTION_VALIDATION_FOCUS : null,
  }
}

export function buildCommentDeepLinkPath(
  parentPath: string,
  commentId: string,
): string {
  const params = new URLSearchParams({
    tab: COMMENT_DEEP_LINK_TAB,
    [COMMENT_DEEP_LINK_COMMENT_ID_PARAM]: commentId,
  })
  return `${parentPath}?${params.toString()}`
}

export function buildExecutionValidationFocusPath(executionId: string): string {
  const params = new URLSearchParams({
    [EXECUTION_VALIDATION_FOCUS_PARAM]: EXECUTION_VALIDATION_FOCUS,
  })
  return `/action-plans/executions/${executionId}?${params.toString()}`
}
