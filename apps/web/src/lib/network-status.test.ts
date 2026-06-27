// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useNetworkStatus } from './network-status'

describe('useNetworkStatus', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reflects navigator.onLine and updates on offline/online events', () => {
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      value: true,
    })

    const { result } = renderHook(() => useNetworkStatus())
    expect(result.current.isOnline).toBe(true)

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: false,
      })
      window.dispatchEvent(new Event('offline'))
    })

    expect(result.current.isOnline).toBe(false)

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: true,
      })
      window.dispatchEvent(new Event('online'))
    })

    expect(result.current.isOnline).toBe(true)
  })
})
