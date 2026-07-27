// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { SignalUnclassifiedBadge } from './signal-unclassified-badge'

afterEach(() => {
  cleanup()
})

describe('SignalUnclassifiedBadge', () => {
  it('renders when responsible id is null including affected-only', () => {
    render(
      <SignalUnclassifiedBadge
        signal={{
          responsible_business_unit_id: null,
        }}
        variant="feed"
      />,
    )
    expect(screen.getByText('Non classifié')).toBeTruthy()
  })

  it('renders nothing when responsible is known', () => {
    const { container } = render(
      <SignalUnclassifiedBadge
        signal={{
          responsible_business_unit_id: 'bu-1',
        }}
        variant="feed"
      />,
    )
    expect(container.textContent).toBe('')
  })
})
