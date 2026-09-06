// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LegalEntryGates } from './legal-entry-gates'

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      isAuthenticated: true,
      bootstrap: {
        user: {
          needs_terms_acceptance: false,
          ai_consent_status: 'granted' as 'granted' | 'declined' | 'undecided',
        },
      },
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/components/legal-consent-sheet', () => ({
  LegalConsentSheet: ({
    kind,
  }: {
    kind: 'terms' | 'ai' | null
  }) =>
    kind
      ? createElement('div', { 'data-testid': 'legal-entry-sheet', 'data-kind': kind })
      : null,
}))

function renderGates() {
  return render(createElement(LegalEntryGates, null, createElement('div', null, 'app')))
}

describe('LegalEntryGates', () => {
  afterEach(() => {
    cleanup()
    authState.current = {
      isAuthenticated: true,
      bootstrap: {
        user: {
          needs_terms_acceptance: false,
          ai_consent_status: 'granted' as 'granted' | 'declined' | 'undecided',
        },
      },
    }
  })

  it('shows terms gate when terms are missing', () => {
    authState.current.bootstrap.user.needs_terms_acceptance = true
    authState.current.bootstrap.user.ai_consent_status = 'undecided'
    renderGates()
    expect(screen.getByTestId('legal-entry-sheet').getAttribute('data-kind')).toBe('terms')
  })

  it('shows AI gate only when undecided after terms', () => {
    authState.current.bootstrap.user.ai_consent_status = 'undecided'
    renderGates()
    expect(screen.getByTestId('legal-entry-sheet').getAttribute('data-kind')).toBe('ai')
  })

  it('does not show an AI gate when declined', () => {
    authState.current.bootstrap.user.ai_consent_status = 'declined'
    renderGates()
    expect(screen.queryByTestId('legal-entry-sheet')).toBeNull()
    expect(screen.getByText('app')).toBeTruthy()
  })

  it('marks app content inert while a legal gate is open', () => {
    authState.current.bootstrap.user.needs_terms_acceptance = true
    renderGates()
    expect(screen.getByText('app').parentElement?.hasAttribute('inert')).toBe(true)
  })

  it('leaves app content interactive when no legal gate is shown', () => {
    renderGates()
    expect(screen.queryByTestId('legal-entry-sheet')).toBeNull()
    expect(screen.getByText('app').parentElement?.hasAttribute('inert')).toBe(false)
  })
})
