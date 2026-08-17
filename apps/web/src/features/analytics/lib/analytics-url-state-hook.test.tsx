// @vitest-environment jsdom

import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createMemoryHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import {
  type AnalyticsUrlState,
  useAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'

const ORG_ID = '11111111-1111-4111-8111-111111111111'

function Probe({ values }: { values: AnalyticsUrlState[] }) {
  values.push(useAnalyticsUrlState())
  return null
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('useAnalyticsUrlState', () => {
  it('keeps the default period stable across rerenders until location.search changes', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-12T10:30:00.000Z'))
    const history = createMemoryHistory('/analytics')
    const values: AnalyticsUrlState[] = []

    const view = render(
      <AppRouteProvider history={history}>
        <Probe values={values} />
      </AppRouteProvider>,
    )
    const initial = values.at(-1)!

    vi.setSystemTime(new Date('2026-08-12T11:30:00.000Z'))
    view.rerender(
      <AppRouteProvider history={history}>
        <Probe values={values} />
      </AppRouteProvider>,
    )

    expect(values.at(-1)).toEqual(initial)

    act(() => {
      history.navigate(`/analytics?organization_id=${ORG_ID}`)
    })

    expect(values.at(-1)).toEqual({
      periodStart: '2026-07-13T11:30:00.000Z',
      periodEnd: '2026-08-12T11:30:00.000Z',
      organizationId: ORG_ID,
      establishmentIds: [],
      q: '',
      recurrence: 'all',
      responsibleBusinessUnitIds: [],
      responsibleBusinessUnitUnassigned: false,
      signalStatuses: [],
    })
  })
})
