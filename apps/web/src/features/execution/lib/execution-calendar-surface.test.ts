// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { installTestMatchMedia } from '@/test/viewport-match-media'

import { isDesktopCalendarSurface } from './execution-calendar-surface'

describe('isDesktopCalendarSurface', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('stays on the band calendar for a large touch screen', () => {
    installTestMatchMedia(true, 'coarse')
    expect(isDesktopCalendarSurface()).toBe(false)
  })

  it('uses the desktop calendar for a fine hovering pointer below the lg breakpoint', () => {
    installTestMatchMedia(false, 'fine')
    expect(isDesktopCalendarSurface()).toBe(true)
  })

  it('stays on the band calendar in the native runtime', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    installTestMatchMedia(true, 'fine')
    expect(isDesktopCalendarSurface()).toBe(false)
  })
})
