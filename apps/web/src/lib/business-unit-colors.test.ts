import { describe, expect, it } from 'vitest'
import { businessUnitPalette, getBusinessUnitColors } from './business-unit-colors'

function luminance(hex: string) {
  const channels = hex.match(/[a-f\d]{2}/gi)!.map((part) => {
    const value = parseInt(part, 16) / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
}

describe('business unit colors', () => {
  it('gives nine distinct high-contrast pastel badges, independent of display order', () => {
    expect(new Set(businessUnitPalette.map((tone) => tone.backgroundColor)).size).toBe(9)
    for (const index of [8, 2, 0, 5, 1, 4, 7, 3, 6]) {
      const tone = getBusinessUnitColors(index)
      expect(tone).toEqual(businessUnitPalette[index])
      expect((luminance(tone.backgroundColor) + 0.05) / (luminance(tone.color) + 0.05)).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('does not wrap to the first palette when more poles are added', () => {
    const tones = Array.from({ length: 100 }, (_, index) => getBusinessUnitColors(index))
    expect(new Set(tones.map((tone) => tone.backgroundColor)).size).toBe(100)
    expect(getBusinessUnitColors(0)).toEqual(businessUnitPalette[0])
  })

  it('keeps missing and invalid slots neutral instead of guessing from a name', () => {
    for (const index of [null, undefined, -1, 1.5, NaN, Infinity]) {
      expect(getBusinessUnitColors(index)).toEqual({ backgroundColor: '#F0EFE9', color: '#555555' })
    }
  })
})
