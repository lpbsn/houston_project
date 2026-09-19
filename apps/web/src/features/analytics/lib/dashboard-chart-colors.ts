export const DESTINATION_CHART_COLORS = {
  waiting: '#D97706',
  interesting: '#2563EB',
  action_plan_in_progress: '#7C3AED',
  resolved_direct: '#0D9488',
  resolved_via_action_plan: '#1F7A4D',
  canceled: '#E24B4A',
} as const

export type DestinationChartKey = keyof typeof DESTINATION_CHART_COLORS

export const UNASSIGNED_POLE_ID = 'unassigned'
export const UNASSIGNED_POLE_COLOR = '#8A8882'

export const POLE_CHART_PALETTE = [
  '#0072B2',
  '#E69F00',
  '#009E73',
  '#CC79A7',
  '#56B4E9',
  '#F0E442',
  '#D55E00',
] as const

const FALLBACK_DESTINATION_COLOR = '#8A8882'

export function destinationChartColor(key: string): string {
  return DESTINATION_CHART_COLORS[key as DestinationChartKey] ?? FALLBACK_DESTINATION_COLOR
}

export function assignPoleColors(
  windows: ReadonlyArray<{ segments: ReadonlyArray<{ pole_id: string }> }>,
): Map<string, string> {
  const colors = new Map<string, string>()
  let paletteIndex = 0
  for (const window of windows) {
    for (const segment of window.segments) {
      if (colors.has(segment.pole_id)) {
        continue
      }
      if (segment.pole_id === UNASSIGNED_POLE_ID) {
        colors.set(segment.pole_id, UNASSIGNED_POLE_COLOR)
        continue
      }
      colors.set(
        segment.pole_id,
        POLE_CHART_PALETTE[paletteIndex % POLE_CHART_PALETTE.length] ?? POLE_CHART_PALETTE[0],
      )
      paletteIndex += 1
    }
  }
  return colors
}

export function poleChartColor(poleId: string, colors: ReadonlyMap<string, string>): string {
  if (poleId === UNASSIGNED_POLE_ID) {
    return UNASSIGNED_POLE_COLOR
  }
  return colors.get(poleId) ?? POLE_CHART_PALETTE[0]
}
