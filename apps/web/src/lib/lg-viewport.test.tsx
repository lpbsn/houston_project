// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { COMPUTER_POINTER_QUERY } from '@/lib/primary-pointer'
import { testMediaMatches } from '@/test/viewport-match-media'

import { LG_MEDIA_QUERY, useLgViewport } from './lg-viewport'

function ViewportProbe({ onValue }: { onValue: (value: boolean) => void }) {
  onValue(useLgViewport())
  return null
}

function DesktopProbe({ onValue }: { onValue: (value: boolean) => void }) {
  onValue(isDesktopWebLanding(useLgViewport()))
  return null
}

function stubMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: testMediaMatches(query, matches),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function installControllableMatchMedia(initial: Record<string, boolean>) {
  const state = { ...initial }
  const listeners = new Map<string, Set<() => void>>()

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      get matches() {
        return state[query] ?? false
      },
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: (_type: string, listener: () => void) => {
        const group = listeners.get(query) ?? new Set<() => void>()
        group.add(listener)
        listeners.set(query, group)
      },
      removeEventListener: (_type: string, listener: () => void) => {
        listeners.get(query)?.delete(listener)
      },
      dispatchEvent: () => false,
    }),
  })

  return {
    set(query: string, matches: boolean) {
      state[query] = matches
      listeners.get(query)?.forEach((listener) => listener())
    },
  }
}

describe('useLgViewport', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('stays false when matchMedia is missing', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: undefined,
    })

    const values: boolean[] = []
    render(createElement(ViewportProbe, { onValue: (value) => values.push(value) }))

    expect(values.at(-1)).toBe(false)
  })

  it('is true on first render when the lg media query matches', () => {
    stubMatchMedia(true)

    const values: boolean[] = []
    render(createElement(ViewportProbe, { onValue: (value) => values.push(value) }))

    expect(values[0]).toBe(true)
    expect(values.at(-1)).toBe(true)
  })

  it('stays a width check when the primary pointer is fine', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: testMediaMatches(query, false, 'fine'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    const values: boolean[] = []
    render(createElement(ViewportProbe, { onValue: (value) => values.push(value) }))

    expect(values[0]).toBe(false)
    expect(values.at(-1)).toBe(false)
  })

  it('follows pointer changes without a first-render flicker on web', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const media = installControllableMatchMedia({
      [LG_MEDIA_QUERY]: false,
      [COMPUTER_POINTER_QUERY]: true,
    })
    const values: boolean[] = []
    render(createElement(DesktopProbe, { onValue: (value) => values.push(value) }))

    expect(values[0]).toBe(true)
    expect(values.every((value) => value)).toBe(true)

    act(() => {
      media.set(COMPUTER_POINTER_QUERY, false)
    })
    expect(values.at(-1)).toBe(false)

    act(() => {
      media.set(LG_MEDIA_QUERY, true)
    })
    expect(values.at(-1)).toBe(true)
  })
})
