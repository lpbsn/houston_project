import { useEffect, useState } from 'react'

import {
  fetchAuthenticatedChatMedia,
  isInlineChatMediaHref,
  resolveChatMediaHref,
} from '../lib/chat-media'

type FetchedChatMedia = {
  src: string
  url: string
  createdByViewer: boolean
}

function revokeCreatedViewerUrl(url: string | null | undefined, href: string | null) {
  if (url && url.startsWith('blob:') && url !== href) {
    URL.revokeObjectURL(url)
  }
}

export function useChatMediaObjectUrl(src: string | null | undefined) {
  const href = resolveChatMediaHref(src)
  const inline = href != null && isInlineChatMediaHref(href)
  const invalid = !href

  const [fetched, setFetched] = useState<FetchedChatMedia | null>(null)
  const [failedSrc, setFailedSrc] = useState<string | null>(null)

  useEffect(() => {
    if (!src || !href || inline) {
      return
    }

    let cancelled = false
    let createdUrl: string | null = null

    void fetchAuthenticatedChatMedia(src).then((url) => {
      if (cancelled) {
        revokeCreatedViewerUrl(url, href)
        return
      }
      if (!url) {
        setFailedSrc(src)
        return
      }
      const created = url.startsWith('blob:') && url !== href
      createdUrl = created ? url : null
      setFetched({ src, url, createdByViewer: created })
    })

    return () => {
      cancelled = true
      revokeCreatedViewerUrl(createdUrl, href)
    }
  }, [src, href, inline])

  const fetchedForSrc = fetched?.src === src ? fetched : null
  const objectUrl = invalid ? null : inline ? href : (fetchedForSrc?.url ?? null)
  const createdByViewer = fetchedForSrc?.createdByViewer ?? false
  const error = invalid || failedSrc === src
  const loading = Boolean(src) && !invalid && !inline && fetchedForSrc == null && failedSrc !== src

  return { objectUrl, createdByViewer, error, loading }
}
