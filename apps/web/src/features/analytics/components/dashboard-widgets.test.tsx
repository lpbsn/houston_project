// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { AnalyticsDashboardMetricComparison } from '@/features/analytics/api'
import {
  ObservationDestinationsCard,
  ObservationVolumeCard,
  PlanOverrunCard,
  ResolutionQualityCard,
  TrendBadge,
} from '@/features/analytics/components/dashboard-widgets'
import { UNASSIGNED_POLE_COLOR, destinationChartColor } from '@/features/analytics/lib/dashboard-chart-colors'
import { formatAbsentPreviousPeriodLabel, formatDashboardPercent, formatOverrunBucketStat } from '@/features/analytics/lib/dashboard-comparisons'
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

const OVERRUN_TOOLTIP =
  'Le taux de dépassement compare le temps de retard à la durée planifiée du plan. Plus le pourcentage est élevé, plus le retard est important par rapport au délai prévu. Exemple : 2 jours de retard sur un plan de 30 jours représentent 6,7 %, tandis que 2 jours de retard sur un plan de 2 jours représentent 100 %.'

describe('PlanOverrunCard', () => {
  it('shows bucket counts as plans and share percent', () => {
    render(createElement(PlanOverrunCard, { data: dashboardResponseFixture().plan_overrun }))

    expect(
      screen.getByText((_, node) => node?.textContent === formatOverrunBucketStat(4, 0.27)),
    ).toBeTruthy()
    expect(
      screen.getAllByText((_, node) => node?.textContent === formatOverrunBucketStat(3, 0.2)).length,
    ).toBeGreaterThan(0)
  })

  it('opens the overrun tooltip from the title trigger and closes on Escape', () => {
    render(createElement(PlanOverrunCard, { data: dashboardResponseFixture().plan_overrun }))

    const trigger = screen.getByRole('button', { name: 'Informations sur le taux de dépassement' })
    expect(trigger.getAttribute('title')).toBeNull()
    expect(screen.queryByText(OVERRUN_TOOLTIP)).toBeNull()

    fireEvent.click(trigger)
    expect(screen.getByText(OVERRUN_TOOLTIP)).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByText(OVERRUN_TOOLTIP)).toBeNull()
  })

  it('closes the overrun tooltip on outside click', async () => {
    render(createElement(PlanOverrunCard, { data: dashboardResponseFixture().plan_overrun }))

    fireEvent.click(screen.getByRole('button', { name: 'Informations sur le taux de dépassement' }))
    expect(screen.getByText(OVERRUN_TOOLTIP)).toBeTruthy()

    await new Promise((resolve) => setTimeout(resolve, 0))
    fireEvent.pointerDown(screen.getByRole('heading', { name: 'Plans d’action en retard' }))
    expect(screen.queryByText(OVERRUN_TOOLTIP)).toBeNull()
  })
})

describe('ResolutionQualityCard', () => {
  it('keeps the zero-star row graphic without a visible 0 étoile label', () => {
    render(createElement(ResolutionQualityCard, { data: dashboardResponseFixture().resolution_quality }))

    expect(screen.queryByText('0 étoile')).toBeNull()
    const zeroStars = screen.getByRole('img', { name: '0 étoile' })
    expect(zeroStars).toBeTruthy()
    expect(zeroStars.textContent?.replace(/\s/g, '')).toBe('☆☆☆☆☆')
  })
})
