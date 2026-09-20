import { useEffect, useState } from 'react'

import {
  fetchAuthenticatedChatMedia,
  isInlineChatMediaHref,
  resolveChatMediaHref,
} from '../lib/chat-media'

export function useChatMediaObjectUrl(src: string | null | undefined) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [createdByViewer, setCreatedByViewer] = useState(false)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(Boolean(src))

  useEffect(() => {
    const href = resolveChatMediaHref(src)
    if (!href) {
      setObjectUrl(null)
      setCreatedByViewer(false)
      setError(true)
      setLoading(false)
      return
    }

    if (isInlineChatMediaHref(href)) {
      setObjectUrl(href)
      setCreatedByViewer(false)
      setError(false)
      setLoading(false)
      return
    }

    let cancelled = false
    let createdUrl: string | null = null
    setLoading(true)
    setError(false)
    setObjectUrl(null)
    setCreatedByViewer(false)

    void fetchAuthenticatedChatMedia(src!).then((url) => {
      if (cancelled) {
        if (url && url.startsWith('blob:') && url !== href) {
          URL.revokeObjectURL(url)
        }
        return
      }
      if (!url) {
        setError(true)
        setLoading(false)
        return
      }
      const created = url.startsWith('blob:') && url !== href
      createdUrl = created ? url : null
      setObjectUrl(url)
      setCreatedByViewer(created)
      setLoading(false)
    })

    return () => {
      cancelled = true
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl)
      }
    }
  }, [src])

  return { objectUrl, createdByViewer, error, loading }
}
