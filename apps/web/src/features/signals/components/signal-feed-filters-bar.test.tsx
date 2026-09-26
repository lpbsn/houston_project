// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { EMPTY_SIGNAL_FEED_FILTERS } from '../lib/signal-feed-filters'
import { SignalFeedFiltersBar } from './signal-feed-filters-bar'

const lgViewportMock = vi.hoisted(() => ({ value: true }))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => lgViewportMock.value,
}))

vi.mock('@/features/auth/lib/authenticated-landing', () => ({
  isDesktopWebLanding: (isLg: boolean) => isLg,
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({ data: undefined }),
}))

afterEach(() => {
  cleanup()
  lgViewportMock.value = true
})

describe('SignalFeedFiltersBar', () => {
  it('renders the desktop filters strip without a top border separator', () => {
    lgViewportMock.value = true
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
    lgViewportMock.value = false
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
