// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const registerOnboarding = vi.fn()
const login = vi.fn()

vi.mock('@/features/auth/api', () => ({
  RegistrationValidationError: class RegistrationValidationError extends Error {
    status: number
    code: string | null
    constructor(message: string, status: number, options?: { code?: string | null }) {
      super(message)
      this.name = 'RegistrationValidationError'
      this.status = status
      this.code = options?.code ?? null
    }
  },
  registerOnboarding: (...args: unknown[]) => registerOnboarding(...args),
  login: (...args: unknown[]) => login(...args),
}))

import { RegistrationValidationError } from '@/features/auth/api'
import { OwnerOrgOnboardingStep } from '../components/owner-org-onboarding-step'
import {
  REGISTRATION_SESSION_STORAGE_KEY,
  clearRegistrationSessionSnapshot,
} from '../lib/registration-session-storage'

afterEach(() => {
  cleanup()
  clearRegistrationSessionSnapshot()
  registerOnboarding.mockReset()
  login.mockReset()
})

beforeEach(() => {
  window.sessionStorage.clear()
})

function fillForm() {
  fireEvent.change(screen.getByLabelText(/code d’invitation/i), {
    target: { value: 'valid-code' },
  })
  fireEvent.change(screen.getByLabelText(/^prénom$/i), { target: { value: 'Alex' } })
  fireEvent.change(screen.getByLabelText(/^nom$/i), { target: { value: 'Owner' } })
  fireEvent.change(screen.getByLabelText(/e-mail/i), {
    target: { value: 'alex@example.com' },
  })
  fireEvent.change(screen.getByLabelText(/^mot de passe$/i), {
    target: { value: 'StrongPass123!' },
  })
  fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
    target: { value: 'StrongPass123!' },
  })
  fireEvent.change(screen.getByLabelText(/organisation/i), {
    target: { value: 'Northwind Group' },
  })
}

describe('OwnerOrgOnboardingStep', () => {
  it('registers without establishment_name and clears sessionStorage', async () => {
    const onRegistered = vi.fn()
    registerOnboarding.mockResolvedValue({
      establishment_id: 'est-1',
      onboarding_session_id: 'sess-1',
    })

    render(createElement(OwnerOrgOnboardingStep, { onRegistered }))
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /continuer/i }))

    await waitFor(() => expect(onRegistered).toHaveBeenCalledWith({
      establishmentId: 'est-1',
      sessionId: 'sess-1',
    }))

    expect(registerOnboarding).toHaveBeenCalledWith(
      expect.not.objectContaining({ establishment_name: expect.anything() }),
    )
    expect(registerOnboarding.mock.calls[0]?.[0]).not.toHaveProperty('establishment_name')
    expect(window.sessionStorage.getItem(REGISTRATION_SESSION_STORAGE_KEY)).toBeNull()
    expect(document.body.textContent).not.toMatch(/draft-/i)
  })

  it('auto-logs in on duplicate_email when credentials are in memory and clears storage', async () => {
    const onRegistered = vi.fn()
    registerOnboarding.mockRejectedValue(
      new RegistrationValidationError('exists', 400, { code: 'duplicate_email' }),
    )
    login.mockResolvedValue({
      pending_onboarding_memberships: [
        {
          id: 'm1',
          establishment_id: 'est-dup',
          establishment_name: 'draft-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
          organization_name: 'Northwind Group',
          establishment_status: 'draft',
          organization_id: 'org-1',
          role: 'owner',
          onboarding_session_id: 'sess-dup',
          can_continue_onboarding: true,
        },
      ],
    })

    render(createElement(OwnerOrgOnboardingStep, { onRegistered }))
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /continuer/i }))

    await waitFor(() =>
      expect(onRegistered).toHaveBeenCalledWith({
        establishmentId: 'est-dup',
        sessionId: 'sess-dup',
      }),
    )
    expect(login).toHaveBeenCalledWith({
      identifier: 'alex@example.com',
      password: 'StrongPass123!',
    })
    expect(registerOnboarding).toHaveBeenCalledTimes(1)
    expect(window.sessionStorage.getItem(REGISTRATION_SESSION_STORAGE_KEY)).toBeNull()
  })

  it('shows login CTA when duplicate_email login fails and does not re-register', async () => {
    const onNavigate = vi.fn()
    registerOnboarding.mockRejectedValue(
      new RegistrationValidationError('exists', 400, { code: 'duplicate_email' }),
    )
    login.mockRejectedValue(new Error('bad credentials'))

    render(
      createElement(OwnerOrgOnboardingStep, {
        onRegistered: vi.fn(),
        onNavigate,
      }),
    )
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /continuer/i }))

    await screen.findByTestId('owner-org-login-cta')
    expect(registerOnboarding).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByTestId('owner-org-login-cta'))
    expect(onNavigate).toHaveBeenCalledWith('/login')
  })

  it('shows 3-step stepper with organization current', () => {
    render(createElement(OwnerOrgOnboardingStep, { onRegistered: vi.fn() }))
    expect(screen.getByTestId('onboarding-stepper')).toBeTruthy()
    expect(screen.getByTestId('onboarding-step-organization').getAttribute('data-state')).toBe(
      'current',
    )
    expect(screen.getByTestId('onboarding-step-structure').getAttribute('data-state')).toBe(
      'upcoming',
    )
  })
})
