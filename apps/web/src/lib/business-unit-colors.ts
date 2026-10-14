/** Stable server-assigned slots. Never derive pole colors from labels or feed order. */
export const businessUnitPalette = [
  { backgroundColor: '#ffeddf', color: '#843b0b' },
  { backgroundColor: '#f0e7fc', color: '#66369a' },
  { backgroundColor: '#fde6f0', color: '#922f61' },
  { backgroundColor: '#e2edff', color: '#28529a' },
  { backgroundColor: '#fff2cc', color: '#755309' },
  { backgroundColor: '#e0f2f3', color: '#176166' },
  { backgroundColor: '#e5f1da', color: '#456326' },
  { backgroundColor: '#eae9ff', color: '#504399' },
  { backgroundColor: '#fce5e3', color: '#973e37' },
] as const

const neutral = { backgroundColor: '#F0EFE9', color: '#555555' }

export function getBusinessUnitColors(index: number | null | undefined) {
  if (index == null || !Number.isSafeInteger(index) || index < 0) return neutral
  if (index < businessUnitPalette.length) return businessUnitPalette[index]
  // Additional poles get additional hues instead of wrapping the nine-color palette.
  // At high counts nearby shades are inevitable; the label remains the identifier.
  const hue = ((index - businessUnitPalette.length) * 137.508 + 30) % 360
  return {
    backgroundColor: `hsl(${hue.toFixed(3)} 65% 93%)`,
    color: `hsl(${hue.toFixed(3)} 65% 25%)`,
  }
}
