import { describe, expect, it } from 'vitest'

import {
  barHeightPercent,
  integerYAxis,
  volumeSegmentLabelVisible,
} from '@/features/analytics/lib/dashboard-chart-scale'

describe('barHeightPercent', () => {
  it('returns 0 when the scale is empty or the count is empty', () => {
    expect(barHeightPercent(4, 0)).toBe(0)
    expect(barHeightPercent(0, 10)).toBe(0)
  })

  it('does not apply a visual floor and keeps segment sums proportional to the window total', () => {
    const scaleMax = 80
    const segments = [1, 12, 65]
    const heights = segments.map((count) => barHeightPercent(count, scaleMax))
    expect(Math.min(...heights)).toBe(barHeightPercent(1, scaleMax))
    expect(heights.reduce((sum, height) => sum + height, 0)).toBeCloseTo(
      barHeightPercent(78, scaleMax),
    )
  })
})

describe('volumeSegmentLabelVisible', () => {
  it('hides labels on small segments without changing their height', () => {
    expect(volumeSegmentLabelVisible(1, 80)).toBe(false)
    expect(volumeSegmentLabelVisible(65, 80)).toBe(true)
    expect(barHeightPercent(1, 80)).toBeCloseTo(1.25)
  })
})

describe('integerYAxis', () => {
  it('uses integer ticks including every count for small volumes', () => {
    expect(integerYAxis(3)).toEqual({ scaleMax: 3, ticks: [0, 1, 2, 3] })
    expect(integerYAxis(0)).toEqual({ scaleMax: 0, ticks: [0] })
  })

  it('uses integer nice ticks that cover a larger max', () => {
    const axis = integerYAxis(78)
    expect(axis.ticks.every((tick) => Number.isInteger(tick))).toBe(true)
    expect(axis.scaleMax).toBeGreaterThanOrEqual(78)
    expect(axis.ticks[0]).toBe(0)
    expect(axis.ticks.at(-1)).toBe(axis.scaleMax)
    expect(axis).toEqual({ scaleMax: 80, ticks: [0, 20, 40, 60, 80] })
  })
})
