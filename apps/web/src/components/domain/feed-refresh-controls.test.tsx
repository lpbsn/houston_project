// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { createRef, type PointerEvent as ReactPointerEvent } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { useFeedPullToRefresh } from './feed-refresh-controls'

function pointerEvent(
  currentTarget: HTMLElement,
  clientY: number,
): ReactPointerEvent<HTMLElement> {
  return {
    clientY,
    currentTarget,
    pointerId: 1,
    pointerType: 'touch',
  } as ReactPointerEvent<HTMLElement>
}

describe('useFeedPullToRefresh', () => {
  it('refreshes from the latest pointer distance before React commits state', () => {
    const scroller = document.createElement('div')
    Object.defineProperty(scroller, 'scrollTop', { configurable: true, value: 0 })
    scroller.hasPointerCapture = vi.fn(() => false)
    const scrollerRef = createRef<HTMLElement>()
    scrollerRef.current = scroller
    const onRefresh = vi.fn()
    const { result } = renderHook(() =>
      useFeedPullToRefresh({ enabled: true, scrollerRef, onRefresh }),
    )

    act(() => {
      result.current.pointerProps.onPointerDown(pointerEvent(scroller, 10))
      result.current.pointerProps.onPointerMove(pointerEvent(scroller, 90))
      result.current.pointerProps.onPointerUp(pointerEvent(scroller, 90))
    })

    expect(onRefresh).toHaveBeenCalledTimes(1)
    expect(result.current.pullDistance).toBe(0)
  })
})
