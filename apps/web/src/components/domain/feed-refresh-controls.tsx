import { useRef, useState, type PointerEvent as ReactPointerEvent, type RefObject } from 'react'
import { LoaderCircle, RefreshCw } from 'lucide-react'

import { TerrainErrorState } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

const PULL_THRESHOLD_PX = 72

export function FeedUpdatesBanner({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="sticky top-0 z-10 px-3 pb-2 pt-2">
      <button
        type="button"
        className="flex min-h-11 w-full items-center justify-center rounded-full border border-[#1B4FD8]/25 bg-[#EEF4FF] px-4 text-sm font-semibold text-[#1B4FD8]"
        onClick={onRefresh}
      >
        Mises à jour disponibles
      </button>
    </div>
  )
}

export function FeedRefreshButton({
  onRefresh,
  disabled = false,
  pending = false,
  className,
}: {
  onRefresh: () => void
  disabled?: boolean
  pending?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      aria-label="Actualiser"
      className={cn(
        'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#5c564e]',
        'hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
        'disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
      onClick={onRefresh}
      disabled={disabled || pending}
    >
      {pending ? (
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
      ) : (
        <RefreshCw className="size-4" aria-hidden />
      )}
    </button>
  )
}

export function FeedContinuationFooter({
  hasMore,
  isLoadingMore,
  hasItems,
  errorMessage,
  onLoadMore,
  onRetry,
}: {
  hasMore: boolean
  isLoadingMore: boolean
  hasItems: boolean
  errorMessage?: string | null
  onLoadMore: () => void
  onRetry: () => void
}) {
  if (errorMessage) {
    return (
      <TerrainErrorState className="mx-3" message={errorMessage} onRetry={onRetry} />
    )
  }
  if (isLoadingMore) {
    return (
      <div className="flex justify-center px-3 py-3 text-sm text-[#7D7B75]">
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        <span className="sr-only">Chargement de la suite</span>
      </div>
    )
  }
  if (hasMore) {
    return (
      <div className="flex justify-center px-3 py-3">
        <button
          type="button"
          className="min-h-11 rounded-full border border-[#1B4FD8]/25 bg-[#EEF4FF] px-5 text-sm font-semibold text-[#1B4FD8]"
          onClick={onLoadMore}
        >
          Charger la suite
        </button>
      </div>
    )
  }
  if (hasItems) {
    return (
      <p className="px-3 py-3 text-center text-xs font-medium text-[#7D7B75]">Fin du feed</p>
    )
  }
  return null
}

export function useFeedPullToRefresh(options: {
  enabled: boolean
  scrollerRef: RefObject<HTMLElement | null>
  onRefresh: () => void
}) {
  const startY = useRef<number | null>(null)
  const pulling = useRef(false)
  const distanceRef = useRef(0)
  const [distance, setDistance] = useState(0)

  function onPointerDown(event: ReactPointerEvent<HTMLElement>) {
    if (!options.enabled || event.pointerType === 'mouse') {
      return
    }
    const scroller = options.scrollerRef.current
    if (!scroller || scroller.scrollTop > 0) {
      return
    }
    startY.current = event.clientY
    pulling.current = true
    distanceRef.current = 0
  }

  function onPointerMove(event: ReactPointerEvent<HTMLElement>) {
    if (!pulling.current || startY.current == null) {
      return
    }
    const scroller = options.scrollerRef.current
    if (!scroller || scroller.scrollTop > 0) {
      pulling.current = false
      startY.current = null
      distanceRef.current = 0
      setDistance(0)
      return
    }
    const next = Math.max(0, event.clientY - startY.current)
    const effectiveDistance = Math.min(next, PULL_THRESHOLD_PX * 1.4)
    distanceRef.current = effectiveDistance
    setDistance(effectiveDistance)
  }

  function finish(event: ReactPointerEvent<HTMLElement>) {
    if (!pulling.current) {
      return
    }
    pulling.current = false
    startY.current = null
    const pulled = distanceRef.current
    distanceRef.current = 0
    setDistance(0)
    if (pulled >= PULL_THRESHOLD_PX) {
      options.onRefresh()
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  return {
    pullDistance: distance,
    pulling: distance > 0,
    pointerProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: finish,
      onPointerCancel: finish,
    },
  }
}

export function FeedPullIndicator({
  distance,
  refreshing,
}: {
  distance: number
  refreshing: boolean
}) {
  if (!refreshing && distance <= 0) {
    return null
  }
  return (
    <div
      className={cn(
        'flex items-center justify-center gap-2 overflow-hidden text-xs font-medium text-[#6b5f52]',
      )}
      style={{ height: refreshing ? 36 : Math.min(distance, 48) }}
    >
      <LoaderCircle className={cn('size-4', refreshing && 'animate-spin')} aria-hidden />
      {refreshing ? 'Actualisation…' : 'Relâcher pour actualiser'}
    </div>
  )
}
