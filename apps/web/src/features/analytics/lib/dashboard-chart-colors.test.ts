import { describe, expect, it } from 'vitest'

import {
  DESTINATION_CHART_COLORS,
  POLE_CHART_PALETTE,
  UNASSIGNED_POLE_COLOR,
  UNASSIGNED_POLE_ID,
  assignPoleColors,
  destinationChartColor,
  poleChartColor,
} from '@/features/analytics/lib/dashboard-chart-colors'

describe('destinationChartColor', () => {
  it('maps every destination key to the expected hex', () => {
    expect(destinationChartColor('waiting')).toBe('#D97706')
    expect(destinationChartColor('interesting')).toBe('#2563EB')
    expect(destinationChartColor('action_plan_in_progress')).toBe('#7C3AED')
    expect(destinationChartColor('resolved_direct')).toBe('#0D9488')
    expect(destinationChartColor('resolved_via_action_plan')).toBe('#1F7A4D')
    expect(destinationChartColor('resolved_via_resolution_request')).toBe('#0891B2')
    expect(destinationChartColor('canceled')).toBe('#E24B4A')
    expect(Object.keys(DESTINATION_CHART_COLORS)).toHaveLength(7)
  })
})

describe('assignPoleColors', () => {
  it('reserves gray for Sans pôle and assigns distinct palette colors in first-seen order', () => {
    const colors = assignPoleColors([
      {
        segments: [
          { pole_id: 'salle' },
          { pole_id: UNASSIGNED_POLE_ID },
        ],
      },
      {
        segments: [
          { pole_id: 'cuisine' },
          { pole_id: 'salle' },
        ],
      },
    ])

    expect(colors.get(UNASSIGNED_POLE_ID)).toBe(UNASSIGNED_POLE_COLOR)
    expect(colors.get('salle')).toBe(POLE_CHART_PALETTE[0])
    expect(colors.get('cuisine')).toBe(POLE_CHART_PALETTE[1])
    expect(new Set([colors.get('salle'), colors.get('cuisine'), colors.get(UNASSIGNED_POLE_ID)]).size).toBe(3)
  })

  it('keeps the same color for a pole across five windows', () => {
    const windows = Array.from({ length: 5 }, () => ({
      segments: [{ pole_id: 'salle' }, { pole_id: 'bar' }],
    }))
    const colors = assignPoleColors(windows)
    expect(colors.get('salle')).toBe(POLE_CHART_PALETTE[0])
    expect(colors.get('bar')).toBe(POLE_CHART_PALETTE[1])
    expect(poleChartColor('salle', colors)).toBe(colors.get('salle'))
  })

  it('reuses palette colors only after every distinct slot is taken', () => {
    const extra = Array.from({ length: POLE_CHART_PALETTE.length + 1 }, (_, index) => ({
      pole_id: `pole-${index}`,
    }))
    const colors = assignPoleColors([{ segments: extra }])
    const assigned = extra.map((segment) => colors.get(segment.pole_id))
    expect(new Set(assigned.slice(0, POLE_CHART_PALETTE.length)).size).toBe(POLE_CHART_PALETTE.length)
    expect(assigned[POLE_CHART_PALETTE.length]).toBe(POLE_CHART_PALETTE[0])
  })
})
