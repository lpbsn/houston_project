// @vitest-environment jsdom

import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  applyPwaUpdate,
  dismissPwaUpdate,
  notifyPwaUpdateAvailable,
  usePwaUpdate,
} from '@/lib/pwa-update'

describe('pwa-update', () => {
  afterEach(() => {
    dismissPwaUpdate()
    cleanup()
  })

  it('starts without a pending refresh', () => {
    const { result } = renderHook(() => usePwaUpdate())
    expect(result.current.needsRefresh).toBe(false)
  })

  it('sets needsRefresh when an update is available', () => {
    const { result } = renderHook(() => usePwaUpdate())

    act(() => {
      notifyPwaUpdateAvailable(vi.fn())
    })

    expect(result.current.needsRefresh).toBe(true)
  })

  it('applyPwaUpdate invokes the stored callback', () => {
    const applyUpdate = vi.fn()

    notifyPwaUpdateAvailable(applyUpdate)
    applyPwaUpdate()

    expect(applyUpdate).toHaveBeenCalledTimes(1)
  })

  it('dismissPwaUpdate hides the prompt without applying the update', () => {
    const applyUpdate = vi.fn()
    const { result } = renderHook(() => usePwaUpdate())

    act(() => {
      notifyPwaUpdateAvailable(applyUpdate)
    })
    act(() => {
      dismissPwaUpdate()
    })

    expect(result.current.needsRefresh).toBe(false)

    applyPwaUpdate()
    expect(applyUpdate).not.toHaveBeenCalled()
  })
})
