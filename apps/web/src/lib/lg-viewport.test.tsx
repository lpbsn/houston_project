// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useLgViewport } from './lg-viewport'

function ViewportProbe({ onValue }: { onValue: (value: boolean) => void }) {
  onValue(useLgViewport())
  return null
}

function stubMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
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

describe('useLgViewport', () => {
  afterEach(() => {
    cleanup()
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

  it('becomes true when the lg media query matches', async () => {
    stubMatchMedia(true)

    const values: boolean[] = []
    render(createElement(ViewportProbe, { onValue: (value) => values.push(value) }))

    await waitFor(() => {
      expect(values.at(-1)).toBe(true)
    })
  })
})
