import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import { cn } from '@/lib/utils'

import type { SignalFeedItem, SignalViewMode } from '../types'
import { SignalCard } from './signal-card'

type SignalFeedPinnedCarouselProps = {
  items: SignalFeedItem[]
  onSelect: (signalId: string) => void
  onOpenActions?: (item: SignalFeedItem) => void
  showEstablishment?: boolean
  viewMode?: SignalViewMode
  className?: string
}

function nearestSnapIndex(scroller: HTMLElement): number {
  const center = scroller.scrollLeft + scroller.clientWidth / 2
  let bestIndex = 0
  let bestDistance = Number.POSITIVE_INFINITY
  const children = Array.from(scroller.children) as HTMLElement[]
  for (let index = 0; index < children.length; index += 1) {
    const child = children[index]
    const childCenter = child.offsetLeft + child.offsetWidth / 2
    const distance = Math.abs(childCenter - center)
    if (distance < bestDistance) {
      bestDistance = distance
      bestIndex = index
    }
  }
  return bestIndex
}

/**
 * Mobile-only horizontal snap carousel for pinned observations.
 * Centered main card with peek of neighbors; arrows drive the same scroll/snap as swipe.
 */
export function SignalFeedPinnedCarousel({
  items,
  onSelect,
  onOpenActions,
  showEstablishment = false,
  viewMode = 'personal',
  className,
}: SignalFeedPinnedCarouselProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    setActiveIndex(0)
    const scroller = scrollerRef.current
    if (scroller) {
      scroller.scrollLeft = 0
    }
  }, [items])

  if (items.length === 0) {
    return null
  }

  const multi = items.length > 1

  function scrollToIndex(nextIndex: number) {
    const scroller = scrollerRef.current
    if (!scroller) {
      return
    }
    const clamped = Math.max(0, Math.min(nextIndex, items.length - 1))
    const child = scroller.children[clamped] as HTMLElement | undefined
    if (!child) {
      return
    }
    const targetLeft = child.offsetLeft - (scroller.clientWidth - child.offsetWidth) / 2
    scroller.scrollTo({ left: Math.max(0, targetLeft), behavior: 'smooth' })
    setActiveIndex(clamped)
  }

  function handleScroll() {
    const scroller = scrollerRef.current
    if (!scroller) {
      return
    }
    setActiveIndex(nearestSnapIndex(scroller))
  }

  return (
    <div
      data-testid="signal-feed-pinned-carousel"
      className={cn('relative', className)}
      role="region"
      aria-roledescription="carousel"
      aria-label="Observations épinglées"
    >
      {multi ? (
        <button
          type="button"
          aria-label="Observation épinglée précédente"
          disabled={activeIndex <= 0}
          className={cn(
            'absolute top-1/2 left-0 z-10 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-[#5c564e] shadow-sm border border-[#E8E6DF] transition disabled:pointer-events-none disabled:opacity-30',
            'focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
          )}
          onClick={() => scrollToIndex(activeIndex - 1)}
        >
          <ChevronLeft className="h-5 w-5" aria-hidden />
        </button>
      ) : null}

      <div
        ref={scrollerRef}
        className={cn(
          'flex snap-x snap-mandatory gap-2 overflow-x-auto overscroll-x-contain scroll-smooth pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden',
          multi ? 'px-[8%]' : undefined,
        )}
        onScroll={handleScroll}
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={cn('shrink-0 snap-center', multi ? 'w-[84%]' : 'w-full')}
          >
            <SignalCard
              item={item}
              variant="pinned"
              onSelect={onSelect}
              onOpenActions={onOpenActions}
              showEstablishment={showEstablishment}
              viewMode={viewMode}
            />
          </div>
        ))}
      </div>

      {multi ? (
        <button
          type="button"
          aria-label="Observation épinglée suivante"
          disabled={activeIndex >= items.length - 1}
          className={cn(
            'absolute top-1/2 right-0 z-10 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-[#5c564e] shadow-sm border border-[#E8E6DF] transition disabled:pointer-events-none disabled:opacity-30',
            'focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
          )}
          onClick={() => scrollToIndex(activeIndex + 1)}
        >
          <ChevronRight className="h-5 w-5" aria-hidden />
        </button>
      ) : null}
    </div>
  )
}
