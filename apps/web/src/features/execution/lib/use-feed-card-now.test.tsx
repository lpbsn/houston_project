// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useFeedCardNow } from '@/features/execution/lib/use-feed-card-now'

function NowConsumer({ label }: { label: string }) {
  const now = useFeedCardNow()
  return createElement('span', { 'data-testid': label }, String(now))
}

function MultiConsumerFixture() {
  return createElement(
    'div',
    null,
    createElement(NowConsumer, { label: 'consumer-a' }),
    createElement(NowConsumer, { label: 'consumer-b' }),
    createElement(NowConsumer, { label: 'consumer-c' }),
  )
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('useFeedCardNow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('renders multiple consumers without an update loop', () => {
    expect(() => render(createElement(MultiConsumerFixture))).not.toThrow()

    const snapshotA = screen.getByTestId('consumer-a').textContent
    expect(screen.getByTestId('consumer-b').textContent).toBe(snapshotA)
    expect(screen.getByTestId('consumer-c').textContent).toBe(snapshotA)
  })

  it('keeps the same snapshot before the tick interval fires', () => {
    render(createElement(MultiConsumerFixture))

    const initialSnapshot = screen.getByTestId('consumer-a').textContent

    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(screen.getByTestId('consumer-a').textContent).toBe(initialSnapshot)
    expect(screen.getByTestId('consumer-b').textContent).toBe(initialSnapshot)
    expect(screen.getByTestId('consumer-c').textContent).toBe(initialSnapshot)
  })

  it('updates the snapshot after 60 seconds', () => {
    render(createElement(MultiConsumerFixture))

    const initialSnapshot = screen.getByTestId('consumer-a').textContent
    let expectedTimestamp = 0

    act(() => {
      vi.advanceTimersByTime(60_000)
      expectedTimestamp = Date.now()
    })

    const updatedSnapshot = screen.getByTestId('consumer-a').textContent
    expect(updatedSnapshot).not.toBe(initialSnapshot)
    expect(updatedSnapshot).toBe(String(expectedTimestamp))
    expect(screen.getByTestId('consumer-b').textContent).toBe(updatedSnapshot)
    expect(screen.getByTestId('consumer-c').textContent).toBe(updatedSnapshot)
  })

  it('clears the interval after the last consumer unmounts', () => {
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval')
    const { unmount } = render(createElement(MultiConsumerFixture))

    unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })
})
