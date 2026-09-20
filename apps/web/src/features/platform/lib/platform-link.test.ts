import { describe, expect, it } from 'vitest'

import { shouldHandlePlatformLinkClick } from './platform-link'

describe('shouldHandlePlatformLinkClick', () => {
  const base = {
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
  }

  it('handles unmodified left clicks', () => {
    expect(shouldHandlePlatformLinkClick(base)).toBe(true)
  })

  it('does not handle modifier or non-left clicks', () => {
    expect(shouldHandlePlatformLinkClick({ ...base, metaKey: true })).toBe(false)
    expect(shouldHandlePlatformLinkClick({ ...base, ctrlKey: true })).toBe(false)
    expect(shouldHandlePlatformLinkClick({ ...base, shiftKey: true })).toBe(false)
    expect(shouldHandlePlatformLinkClick({ ...base, altKey: true })).toBe(false)
    expect(shouldHandlePlatformLinkClick({ ...base, button: 1 })).toBe(false)
    expect(shouldHandlePlatformLinkClick({ ...base, defaultPrevented: true })).toBe(false)
  })
})
