// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { EMPTY_SIGNAL_FEED_FILTERS } from '../lib/signal-feed-filters'
import { SignalFeedFiltersBar } from './signal-feed-filters-bar'

const runtimeMock = vi.hoisted(() => ({ value: 'web' }))

vi.mock('@/lib/runtime', () => ({
  getAppRuntime: () => runtimeMock.value,
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({ data: undefined }),
}))

afterEach(() => {
  cleanup()
  runtimeMock.value = 'web'
})

describe('SignalFeedFiltersBar', () => {
  it('renders the desktop filters strip without a top border separator', () => {
    runtimeMock.value = 'web'
    render(
      <SignalFeedFiltersBar
        establishmentId="est-1"
        filters={EMPTY_SIGNAL_FEED_FILTERS}
        onFiltersChange={vi.fn()}
      />,
    )

    const bar = screen.getByLabelText('Filtres des observations')
    expect(bar.className).not.toContain('border-t')
    expect(bar.className).toContain('bg-white')
  })

  it('keeps mobile chips strip without introducing a top border', () => {
    runtimeMock.value = 'native'
    render(
      <SignalFeedFiltersBar
        establishmentId="est-1"
        filters={EMPTY_SIGNAL_FEED_FILTERS}
        onFiltersChange={vi.fn()}
      />,
    )

    const bar = screen.getByLabelText('Filtres des observations')
    expect(bar.className).not.toContain('border-t')
  })
})
