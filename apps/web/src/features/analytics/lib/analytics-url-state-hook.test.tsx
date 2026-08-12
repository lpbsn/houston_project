// @vitest-environment jsdom

import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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
  window.history.replaceState(null, '', '/')
})

describe('useAnalyticsUrlState', () => {
  it('keeps the default period stable across rerenders until location.search changes', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-12T10:30:00.000Z'))
    window.history.replaceState(null, '', '/analytics')
    const values: AnalyticsUrlState[] = []

    const view = render(<Probe values={values} />)
    const initial = values.at(-1)!

    vi.setSystemTime(new Date('2026-08-12T11:30:00.000Z'))
    view.rerender(<Probe values={values} />)

    expect(values.at(-1)).toEqual(initial)

    act(() => {
      window.history.pushState(null, '', `/analytics?organization_id=${ORG_ID}`)
    })

    expect(values.at(-1)).toEqual({
      periodStart: '2026-07-13T11:30:00.000Z',
      periodEnd: '2026-08-12T11:30:00.000Z',
      organizationId: ORG_ID,
    })
  })
})
