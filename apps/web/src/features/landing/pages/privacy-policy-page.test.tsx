// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { privacyPolicyContent } from '../content'
import { PrivacyPolicyPage } from './privacy-policy-page'

afterEach(() => {
  cleanup()
})

describe('PrivacyPolicyPage', () => {
  it('renders the public privacy policy facts used for stores', () => {
    render(<PrivacyPolicyPage />)

    expect(screen.getByTestId('privacy-policy-page')).toBeTruthy()
    expect(
      screen.getByRole('heading', { level: 1, name: privacyPolicyContent.pageTitle }),
    ).toBeTruthy()
    expect(screen.getByText(/openai-v1/i)).toBeTruthy()
    expect(screen.getByText(/classement analytics/i)).toBeTruthy()
    expect(screen.queryByText(/hors du consentement/i)).toBeNull()
    expect(screen.getByText(/Firebase Cloud Messaging/i)).toBeTruthy()
    expect(screen.getByText(/Railway Corporation/i)).toBeTruthy()
  })
})
