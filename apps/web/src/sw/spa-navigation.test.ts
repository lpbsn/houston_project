import { describe, expect, it } from 'vitest'

import { shouldBypassSpaNavigation } from './spa-navigation-policy'

describe('spa-navigation', () => {
  it('serves SPA routes through navigation fallback', () => {
    expect(shouldBypassSpaNavigation('/signals/abc')).toBe(false)
    expect(shouldBypassSpaNavigation('/profile')).toBe(false)
    expect(shouldBypassSpaNavigation('/')).toBe(false)
  })

  it('bypasses API and WebSocket paths via denylist', () => {
    expect(shouldBypassSpaNavigation('/api/v1/notifications/')).toBe(true)
    expect(shouldBypassSpaNavigation('/ws/chat/room-1/')).toBe(true)
  })
})
