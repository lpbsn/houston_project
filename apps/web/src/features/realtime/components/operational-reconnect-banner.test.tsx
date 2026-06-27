// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { OperationalReconnectBanner } from './operational-reconnect-banner'

describe('OperationalReconnectBanner', () => {
  afterEach(() => {
    cleanup()
  })

  it.each(['idle', 'connecting', 'connected'] as const)(
    'is hidden when status is %s',
    (status) => {
      render(<OperationalReconnectBanner status={status} />)
      expect(screen.queryByRole('status')).toBeNull()
    },
  )

  it('shows reconnecting label', () => {
    render(<OperationalReconnectBanner status="reconnecting" />)
    expect(screen.getByText('Reconnexion en cours…')).toBeTruthy()
  })

  it('shows disconnected label', () => {
    render(<OperationalReconnectBanner status="disconnected" />)
    expect(screen.getByText('Connexion perdue')).toBeTruthy()
  })
})
