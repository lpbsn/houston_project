import { describe, expect, it } from 'vitest'

import { terrainPageMotionProps } from '@/lib/terrain-motion'

describe('terrainPageMotionProps', () => {
  it('skips translation when reduced motion is on', () => {
    expect(terrainPageMotionProps(true, 'forward', false)).toEqual({})
  })

  it('uses a short horizontal shift only for mobile hierarchical navigation', () => {
    const forward = terrainPageMotionProps(false, 'forward', false)
    const back = terrainPageMotionProps(false, 'back', false)
    const primary = terrainPageMotionProps(false, 'fade', false)
    const desktop = terrainPageMotionProps(false, 'forward', true)

    expect(forward.variants?.enter('forward')).toEqual({ opacity: 0, x: 16 })
    expect(back.variants?.exit('back')).toEqual({ opacity: 0, x: 16 })
    expect(primary.variants?.enter('fade')).toEqual({ opacity: 0 })
    expect(desktop.variants?.enter('forward')).toEqual({ opacity: 0 })
    expect(forward.transition).toMatchObject({ duration: 0.18 })
  })
})
