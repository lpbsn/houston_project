const SMALL_VOLUME_MAX = 5
const TARGET_TICK_COUNT = 4

function niceNumber(value: number, round: boolean): number {
  const exponent = Math.floor(Math.log10(value))
  const fraction = value / 10 ** exponent
  let niceFraction: number
  if (round) {
    if (fraction < 1.5) {
      niceFraction = 1
    } else if (fraction < 3) {
      niceFraction = 2
    } else if (fraction < 7) {
      niceFraction = 5
    } else {
      niceFraction = 10
    }
  } else if (fraction <= 1) {
    niceFraction = 1
  } else if (fraction <= 2) {
    niceFraction = 2
  } else if (fraction <= 5) {
    niceFraction = 5
  } else {
    niceFraction = 10
  }
  return niceFraction * 10 ** exponent
}

export const VOLUME_PLOT_HEIGHT_PX = 176
const VOLUME_SEGMENT_LABEL_MIN_PX = 22

export function barHeightPercent(count: number, scaleMax: number): number {
  if (scaleMax <= 0 || count <= 0) {
    return 0
  }
  return (count / scaleMax) * 100
}

export function volumeSegmentLabelVisible(count: number, scaleMax: number): boolean {
  if (scaleMax <= 0 || count <= 0) {
    return false
  }
  return (count / scaleMax) * VOLUME_PLOT_HEIGHT_PX >= VOLUME_SEGMENT_LABEL_MIN_PX
}

export function integerYAxis(maxTotal: number): { scaleMax: number; ticks: number[] } {
  if (maxTotal <= 0) {
    return { scaleMax: 0, ticks: [0] }
  }
  if (maxTotal <= SMALL_VOLUME_MAX) {
    return {
      scaleMax: maxTotal,
      ticks: Array.from({ length: maxTotal + 1 }, (_, index) => index),
    }
  }
  const step = Math.max(1, niceNumber(maxTotal / TARGET_TICK_COUNT, true))
  const scaleMax = Math.ceil(maxTotal / step) * step
  const ticks: number[] = []
  for (let value = 0; value <= scaleMax; value += step) {
    ticks.push(value)
  }
  return { scaleMax, ticks }
}
