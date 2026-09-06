// @vitest-environment jsdom

import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LegalConsentSheet } from './legal-consent-sheet'

vi.mock('@/features/auth/api', () => ({
  AuthApiError: class AuthApiError extends Error {},
  acceptCurrentAiConsent: vi.fn(),
  acceptCurrentTerms: vi.fn(),
  declineCurrentAiConsent: vi.fn(),
}))

afterEach(() => {
  cleanup()
})

describe('LegalConsentSheet dismissible', () => {
  it('disables the scrim when allowDismiss is false', () => {
    const onClose = vi.fn()
    const { container } = render(
      <LegalConsentSheet
        kind="terms"
        allowDismiss={false}
        onClose={onClose}
        onAccepted={() => undefined}
      />,
    )

    const scrim = container.querySelector('button[disabled]')
    expect(scrim).not.toBeNull()
    fireEvent.click(scrim!)
    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes from the scrim when allowDismiss is true', () => {
    const onClose = vi.fn()
    const { container } = render(
      <LegalConsentSheet kind="terms" allowDismiss onClose={onClose} onAccepted={() => undefined} />,
    )

    const scrim = container.querySelector('button[aria-label="Fermer"]')
    expect(scrim).not.toBeNull()
    expect(scrim).not.toHaveProperty('disabled', true)
    fireEvent.click(scrim!)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
