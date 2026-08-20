// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  dismissTopNativeOverlay,
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

  it('returns false when the stack is empty', () => {
    expect(dismissTopNativeOverlay()).toBe(false)
  })

  it('does not dismiss after unregister', () => {
    const dismiss = vi.fn()
    const unregister = registerNativeOverlayDismiss(dismiss)
    unregister()

    expect(dismissTopNativeOverlay()).toBe(false)
    expect(dismiss).not.toHaveBeenCalled()
  })
})
