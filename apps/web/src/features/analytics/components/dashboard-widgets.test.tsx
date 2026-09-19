// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { AnalyticsDashboardMetricComparison } from '@/features/analytics/api'
import {
  ObservationDestinationsCard,
  ObservationVolumeCard,
  TrendBadge,
} from '@/features/analytics/components/dashboard-widgets'
import { UNASSIGNED_POLE_COLOR, destinationChartColor } from '@/features/analytics/lib/dashboard-chart-colors'
import { formatAbsentPreviousPeriodLabel, formatDashboardPercent } from '@/features/analytics/lib/dashboard-comparisons'
import {
  dashboardResponseFixture,
  observationVolumeChartFixture,
} from '@/features/analytics/lib/dashboard-test-fixture'

afterEach(() => {
  cleanup()
})

function cssBackground(hex: string): string {
  const node = document.createElement('span')
  node.style.backgroundColor = hex
  return node.style.backgroundColor
}

function comparison(
  overrides: Partial<AnalyticsDashboardMetricComparison> = {},
): AnalyticsDashboardMetricComparison {
  return {
    current_value: 10,
    previous_value: 8,
    absolute_delta: 2,
    relative_change: 0.25,
    relative_change_status: 'computed',
    coverage: 'complete',
    ...overrides,
  }
}

describe('TrendBadge', () => {
  it('shows an up arrow for a positive delta', () => {
    const { container } = render(
      createElement(TrendBadge, {
        comparison: comparison({ absolute_delta: 3 }),
        sense: 'neutral',
        format: 'count',
        periodDays: 7,
      }),
    )

    expect(container.querySelector('.lucide-arrow-up-right')).toBeTruthy()
    expect(container.querySelector('.lucide-arrow-down-right')).toBeNull()
  })

  it('shows a down arrow for a negative delta', () => {
    const { container } = render(
      createElement(TrendBadge, {
        comparison: comparison({ absolute_delta: -3 }),
        sense: 'neutral',
        format: 'count',
        periodDays: 7,
      }),
    )

    expect(container.querySelector('.lucide-arrow-down-right')).toBeTruthy()
    expect(container.querySelector('.lucide-arrow-up-right')).toBeNull()
  })

  it('shows no arrow when the displayed delta is zero', () => {
    const { container } = render(
      createElement(TrendBadge, {
        comparison: comparison({
          current_value: 8,
          previous_value: 8,
          absolute_delta: 0,
          relative_change: 0,
        }),
        sense: 'neutral',
        format: 'count',
        periodDays: 7,
      }),
    )

    expect(container.querySelector('.lucide-arrow-up-right')).toBeNull()
    expect(container.querySelector('.lucide-arrow-down-right')).toBeNull()
    expect(container.textContent).toBe('')
  })

  it('hides a percent badge that would round to 0 %', () => {
    const { container } = render(
      createElement(TrendBadge, {
        comparison: comparison({
          current_value: 1.004,
          previous_value: 1,
          absolute_delta: 0.004,
          relative_change: 0.004,
        }),
        sense: 'positive-up',
        format: 'percent',
        periodDays: 7,
      }),
    )

    expect(container.textContent).toBe('')
  })

  it('still shows the absent-previous-period label', () => {
    const { container } = render(
      createElement(TrendBadge, {
        comparison: comparison({
          current_value: 4,
          previous_value: 0,
          absolute_delta: 4,
          relative_change: null,
          relative_change_status: 'undefined_previous_zero',
        }),
        sense: 'negative-up',
        format: 'count',
        periodDays: 7,
      }),
    )

    expect(container.textContent).toBe(formatAbsentPreviousPeriodLabel(7))
    expect(container.querySelector('.lucide-arrow-up-right')).toBeNull()
  })
})

describe('ObservationVolumeCard', () => {
  it('defaults to responsible pole mode and keeps bars non-interactive', () => {
    const { container } = render(
      createElement(ObservationVolumeCard, {
        volume: observationVolumeChartFixture(),
        periodDays: 7,
      }),
    )

    expect(container.querySelector('[data-volume-mode="responsible"]')).toBeTruthy()
    expect(container.querySelector('[data-volume-detail]')).toBeNull()
    expect(container.querySelectorAll('[data-volume-window]')).toHaveLength(5)
    expect(container.querySelector('button[data-volume-window]')).toBeNull()

    fireEvent.click(container.querySelector('[data-volume-mode-option="affected"]') as HTMLElement)
    expect(container.querySelector('[data-volume-mode="affected"]')).toBeTruthy()
  })

  it('does not paint segments on a zero window and matches Sans pôle legend color', () => {
    const { container } = render(
      createElement(ObservationVolumeCard, {
        volume: observationVolumeChartFixture(),
        periodDays: 7,
      }),
    )

    fireEvent.click(container.querySelector('[data-volume-mode-option="affected"]') as HTMLElement)

    const zeroColumn = container.querySelector('[data-volume-window="four_periods_ago"]')
    expect(zeroColumn?.querySelectorAll('[data-pole-id]')).toHaveLength(0)
    const stackedBar = zeroColumn?.querySelector('div')
    expect(stackedBar?.style.height).toBe('0%')

    const unassignedSegment = container.querySelector('[data-pole-id="unassigned"]')
    const unassignedLegend = container.querySelector('[data-legend-pole-id="unassigned"]')
    expect(unassignedSegment).toBeTruthy()
    expect(unassignedLegend).toBeTruthy()
    expect((unassignedSegment as HTMLElement).style.backgroundColor).toBe(
      (unassignedLegend as HTMLElement).style.backgroundColor,
    )
    expect((unassignedLegend as HTMLElement).style.backgroundColor).toBe(
      cssBackground(UNASSIGNED_POLE_COLOR),
    )
  })
})

describe('ObservationDestinationsCard', () => {
  it('uses the same hex on the stacked bar and the legend swatch', () => {
    const destinations = dashboardResponseFixture().observation_destinations
    const { container } = render(
      createElement(ObservationDestinationsCard, {
        destinations,
        periodDays: 7,
      }),
    )

    const waitingBar = screen.getByRole('button', {
      name: `En attente ${formatDashboardPercent(destinations.waiting.share)}`,
    })
    const waitingSwatch = container.querySelector('[data-destination-swatch="waiting"]')
    expect(waitingBar.style.backgroundColor).toBe(cssBackground(destinationChartColor('waiting')))
    expect((waitingSwatch as HTMLElement).style.backgroundColor).toBe(waitingBar.style.backgroundColor)
    expect(waitingBar.style.width).toBe(`${(destinations.waiting.share ?? 0) * 100}%`)
  })
})
