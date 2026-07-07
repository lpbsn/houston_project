import { useEffect, useRef } from 'react'

import { cn } from '@/lib/utils'

export const WHEEL_ITEM_HEIGHT = 36
export const WHEEL_VISIBLE_ROWS = 5
export const WHEEL_PICKER_HEIGHT = WHEEL_ITEM_HEIGHT * WHEEL_VISIBLE_ROWS
const PADDING_ROWS = Math.floor(WHEEL_VISIBLE_ROWS / 2)

export type WheelColumnOption = {
  value: string
  label: string
}

export type WheelColumnProps = {
  label: string
  options: WheelColumnOption[]
  value: string
  onChange: (next: string) => void
}

function releaseScrollSync(
  container: HTMLDivElement,
  targetTop: number,
  previousBehavior: string,
  isSyncingScrollRef: { current: boolean },
) {
  if (Math.abs(container.scrollTop - targetTop) <= 1) {
    container.style.scrollBehavior = previousBehavior
    isSyncingScrollRef.current = false
    return
  }
  window.requestAnimationFrame(() =>
    releaseScrollSync(container, targetTop, previousBehavior, isSyncingScrollRef),
  )
}

export function WheelColumn({ label, options, value, onChange }: WheelColumnProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const isSyncingScrollRef = useRef(false)
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  )

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }
    isSyncingScrollRef.current = true
    const previousBehavior = container.style.scrollBehavior
    const targetTop = selectedIndex * WHEEL_ITEM_HEIGHT
    container.style.scrollBehavior = 'auto'
    container.scrollTop = targetTop

    const handleScrollEnd = () => {
      container.style.scrollBehavior = previousBehavior
      isSyncingScrollRef.current = false
    }

    if ('onscrollend' in container) {
      container.addEventListener('scrollend', handleScrollEnd, { once: true })
      return () => {
        container.removeEventListener('scrollend', handleScrollEnd)
        isSyncingScrollRef.current = false
      }
    }

    window.requestAnimationFrame(() =>
      releaseScrollSync(container, targetTop, previousBehavior, isSyncingScrollRef),
    )
    return () => {
      isSyncingScrollRef.current = false
    }
  }, [selectedIndex])

  function handleScroll() {
    if (isSyncingScrollRef.current) {
      return
    }
    const container = containerRef.current
    if (!container) {
      return
    }
    const index = Math.round(container.scrollTop / WHEEL_ITEM_HEIGHT)
    const clamped = Math.min(Math.max(index, 0), options.length - 1)
    const next = options[clamped]?.value
    if (next && next !== value) {
      onChange(next)
    }
  }

  return (
    <div className="relative flex-1">
      <p className="sr-only">{label}</p>
      <div
        ref={containerRef}
        className="overflow-y-auto scroll-smooth [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        style={{ height: WHEEL_PICKER_HEIGHT, scrollSnapType: 'y mandatory' }}
        onScroll={handleScroll}
        aria-label={label}
      >
        {Array.from({ length: PADDING_ROWS }, (_, index) => (
          <div key={`pad-top-${index}`} style={{ height: WHEEL_ITEM_HEIGHT }} aria-hidden />
        ))}
        {options.map((option) => {
          const selected = option.value === value
          return (
            <button
              key={option.value}
              type="button"
              className={cn(
                'flex w-full items-center justify-center px-2 text-sm',
                selected ? 'font-medium text-[#1B4FD8]' : 'text-[#7D7B75]',
              )}
              style={{ height: WHEEL_ITEM_HEIGHT, scrollSnapAlign: 'center' }}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </button>
          )
        })}
        {Array.from({ length: PADDING_ROWS }, (_, index) => (
          <div key={`pad-bottom-${index}`} style={{ height: WHEEL_ITEM_HEIGHT }} aria-hidden />
        ))}
      </div>
    </div>
  )
}

export function toWheelColumnOptions(values: string[]): WheelColumnOption[] {
  return values.map((value) => ({ value, label: value }))
}
