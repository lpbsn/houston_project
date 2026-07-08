export const COMMENT_DEEP_LINK_TAB = 'comments'
export const COMMENT_DEEP_LINK_COMMENT_ID_PARAM = 'commentId'

export type DetailDeepLink = {
  tab: typeof COMMENT_DEEP_LINK_TAB | null
  commentId: string | null
}

export function parseDetailDeepLink(search: string): DetailDeepLink {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const tab = params.get('tab')
  const commentId = params.get(COMMENT_DEEP_LINK_COMMENT_ID_PARAM)?.trim() ?? null

  return {
    tab: tab === COMMENT_DEEP_LINK_TAB ? COMMENT_DEEP_LINK_TAB : null,
    commentId: commentId && commentId.length > 0 ? commentId : null,
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

export function readCurrentDetailDeepLink(): DetailDeepLink {
  if (typeof window === 'undefined') {
    return { tab: null, commentId: null }
  }
  return parseDetailDeepLink(window.location.search)
}
