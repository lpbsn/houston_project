import { describe, expect, it } from 'vitest'

import { visualKeyboardOverlap } from './composer-keyboard-inset'

describe('visualKeyboardOverlap', () => {
  it('returns the bottom overlap of the layout viewport', () => {
    expect(
      visualKeyboardOverlap({
        innerHeight: 800,
        visualHeight: 500,
        offsetTop: 0,
      }),
    ).toBe(300)
  })

  it('includes the visual viewport offset', () => {
    expect(
      visualKeyboardOverlap({
        innerHeight: 800,
        visualHeight: 450,
        offsetTop: 50,
      }),
    ).toBe(300)
  })

  it('clamps a negative overlap to zero', () => {
    expect(
      visualKeyboardOverlap({
        innerHeight: 700,
        visualHeight: 800,
        offsetTop: 0,
      }),
    ).toBe(0)
  })

  it('rounds fractional pixels', () => {
    expect(
      visualKeyboardOverlap({
        innerHeight: 800,
        visualHeight: 500.4,
        offsetTop: 0.4,
      }),
    ).toBe(299)
  })
})
