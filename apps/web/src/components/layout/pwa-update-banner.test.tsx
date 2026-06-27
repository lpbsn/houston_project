// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PwaUpdateBanner } from './pwa-update-banner'
import { dismissPwaUpdate, notifyPwaUpdateAvailable } from '@/lib/pwa-update'

describe('PwaUpdateBanner', () => {
  afterEach(() => {
    dismissPwaUpdate()
    cleanup()
  })

  it('is hidden when no update is pending', () => {
    render(<PwaUpdateBanner />)
    expect(screen.queryByText('Une nouvelle version est disponible')).toBeNull()
  })

  it('shows reload and dismiss actions when an update is pending', () => {
    notifyPwaUpdateAvailable(vi.fn())
    render(<PwaUpdateBanner />)

    expect(screen.getByText('Une nouvelle version est disponible')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Recharger' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Plus tard' })).toBeTruthy()
  })

  it('dismisses the banner when Plus tard is clicked', () => {
    notifyPwaUpdateAvailable(vi.fn())
    render(<PwaUpdateBanner />)

    fireEvent.click(screen.getByRole('button', { name: 'Plus tard' }))

    expect(screen.queryByText('Une nouvelle version est disponible')).toBeNull()
  })
})
