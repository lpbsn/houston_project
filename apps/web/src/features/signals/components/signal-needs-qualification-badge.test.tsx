// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { SignalNeedsQualificationBadge } from './signal-needs-qualification-badge'

afterEach(() => {
  cleanup()
})

describe('SignalNeedsQualificationBadge', () => {
  it('renders for unassigned open signals', () => {
    render(
      <SignalNeedsQualificationBadge
        signal={{ routing_status: 'unassigned', status: 'open' }}
        variant="feed"
      />,
    )
    expect(screen.getByText('À qualifier')).toBeTruthy()
  })

  it('hides for resolved routing or terminal lifecycle', () => {
    const { rerender } = render(
      <SignalNeedsQualificationBadge
        signal={{ routing_status: 'resolved', status: 'open' }}
        variant="feed"
      />,
    )
    expect(screen.queryByText('À qualifier')).toBeNull()

    rerender(
      <SignalNeedsQualificationBadge
        signal={{ routing_status: 'unassigned', status: 'resolved' }}
        variant="feed"
      />,
    )
    expect(screen.queryByText('À qualifier')).toBeNull()
  })
})
