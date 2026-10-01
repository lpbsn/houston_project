// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  dismissTopNativeOverlay,
  isTopNativeOverlay,
  registerNativeOverlayDismiss,
  resetNativeOverlayDismissForTests,
} from './native-overlay-dismiss'

describe('native overlay dismiss stack', () => {
  afterEach(() => {
    resetNativeOverlayDismissForTests()
  })

  it('dismisses the most recently registered overlay first', () => {
    const older = vi.fn()
    const newer = vi.fn()
    registerNativeOverlayDismiss(older)
    registerNativeOverlayDismiss(newer)

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(newer).toHaveBeenCalledTimes(1)
    expect(older).not.toHaveBeenCalled()

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(older).toHaveBeenCalledTimes(1)
  })

  it('keeps a callback that refuses to close', () => {
    const dismiss = vi.fn(() => false)
    registerNativeOverlayDismiss(dismiss)

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(dismissTopNativeOverlay()).toBe(true)
    expect(dismiss).toHaveBeenCalledTimes(2)
  })

  it('returns false when the stack is empty', () => {
    expect(dismissTopNativeOverlay()).toBe(false)
  })

  it('reports only the most recently registered overlay as top', () => {
    const older = vi.fn()
    const newer = vi.fn()
    const unregisterOlder = registerNativeOverlayDismiss(older)
    expect(isTopNativeOverlay(older)).toBe(true)
    expect(isTopNativeOverlay(newer)).toBe(false)

    const unregisterNewer = registerNativeOverlayDismiss(newer)
    expect(isTopNativeOverlay(newer)).toBe(true)
    expect(isTopNativeOverlay(older)).toBe(false)

    unregisterNewer()
    expect(isTopNativeOverlay(older)).toBe(true)
    unregisterOlder()
    expect(isTopNativeOverlay(older)).toBe(false)
  })

  it('does not dismiss after unregister', () => {
    const dismiss = vi.fn()
    const unregister = registerNativeOverlayDismiss(dismiss)
    unregister()

    expect(dismissTopNativeOverlay()).toBe(false)
    expect(dismiss).not.toHaveBeenCalled()
  })
})
