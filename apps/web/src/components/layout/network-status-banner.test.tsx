// @vitest-environment jsdom

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { NetworkStatusBanner } from './network-status-banner'
import { OFFLINE_BANNER_MESSAGE } from '@/lib/network-error'

describe('NetworkStatusBanner', () => {
  it('is hidden when online', () => {
    render(<NetworkStatusBanner isOnline={true} />)
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('shows offline status with accessible role when offline', () => {
    render(<NetworkStatusBanner isOnline={false} />)

    const banner = screen.getByRole('status')
    expect(banner.textContent).toBe(OFFLINE_BANNER_MESSAGE)
  })
})
