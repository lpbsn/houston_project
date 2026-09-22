import { useEffect, useState } from 'react'

import {
  fetchAuthenticatedCommentMedia,
  isInlineCommentMediaHref,
  resolveCommentMediaHref,
} from '../lib/comment-media'

type FetchedCommentMedia = {
  src: string
  url: string
}

function revokeCreatedViewerUrl(url: string | null | undefined, href: string | null) {
  if (url && url.startsWith('blob:') && url !== href) {
    URL.revokeObjectURL(url)
  }
}

export function useCommentMediaObjectUrl(src: string | null | undefined) {
  const href = resolveCommentMediaHref(src)
  const inline = href != null && isInlineCommentMediaHref(href)
  const invalid = !href
  const [fetched, setFetched] = useState<FetchedCommentMedia | null>(null)
  const [failedSrc, setFailedSrc] = useState<string | null>(null)

  useEffect(() => {
    if (!src || !href || inline) {
      return
    }
    let cancelled = false
    let createdUrl: string | null = null
    void fetchAuthenticatedCommentMedia(src).then((url) => {
      if (cancelled) {
        revokeCreatedViewerUrl(url, href)
        return
      }
      if (!url) {
        setFailedSrc(src)
        return
      }
      createdUrl = url.startsWith('blob:') && url !== href ? url : null
      setFetched({ src, url })
    })
    return () => {
      cancelled = true
      revokeCreatedViewerUrl(createdUrl, href)
    }
  }, [src, href, inline])

  const fetchedForSrc = fetched?.src === src ? fetched : null
  const objectUrl = invalid ? null : inline ? href : (fetchedForSrc?.url ?? null)
  const error = invalid || failedSrc === src
  const loading = Boolean(src) && !invalid && !inline && fetchedForSrc == null && failedSrc !== src
  return { objectUrl, error, loading }
}
