import { useCallback, useEffect, useRef, useState } from 'react'

import {
  queryKeyMatchesPrefix,
  registerFeedReadingSession,
} from '@/lib/feed-external-updates'

export function useFeedListSession(options: {
  queryKeyPrefix: readonly unknown[] | null
  onRemove: (entityId: string) => void
}) {
  const atTopRef = useRef(true)
  const interactingRef = useRef(false)
  const onRemoveRef = useRef(options.onRemove)
  const [updatesAvailable, setUpdatesAvailable] = useState(false)

  useEffect(() => {
    onRemoveRef.current = options.onRemove
  }, [options.onRemove])

  useEffect(() => {
    const prefix = options.queryKeyPrefix
    if (!prefix) {
      return
    }
    return registerFeedReadingSession({
      matches: (queryKey) => queryKeyMatchesPrefix(queryKey, prefix),
      atTop: () => atTopRef.current,
      interacting: () => interactingRef.current,
      onDefer: () => setUpdatesAvailable(true),
      onRemove: (entityId) => onRemoveRef.current(entityId),
    })
  }, [options.queryKeyPrefix])

  const clearUpdates = useCallback(() => setUpdatesAvailable(false), [])
  const markUpdates = useCallback(() => setUpdatesAvailable(true), [])
  const setReadingEdge = useCallback((edge: { atTop: boolean; interacting: boolean }) => {
    atTopRef.current = edge.atTop
    interactingRef.current = edge.interacting
  }, [])

  return {
    updatesAvailable,
    clearUpdates,
    markUpdates,
    setReadingEdge,
  }
}
