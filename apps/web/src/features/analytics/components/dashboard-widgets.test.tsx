// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { AnalyticsDashboardMetricComparison } from '@/features/analytics/api'
import { TrendBadge } from '@/features/analytics/components/dashboard-widgets'
import { formatAbsentPreviousPeriodLabel } from '@/features/analytics/lib/dashboard-comparisons'

afterEach(() => {
  cleanup()
})

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
