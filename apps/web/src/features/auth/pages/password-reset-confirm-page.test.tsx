// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRouteProvider } from '@/app/app-routes'
import { createMemoryHistory } from '@/app/app-history'

const confirmPasswordReset = vi.hoisted(() => vi.fn())
const logout = vi.hoisted(() => vi.fn())

vi.mock('@/features/auth/api', () => ({
  AuthApiError: class AuthApiError extends Error {
    status: number
    code: string | null
    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.name = 'AuthApiError'
      this.status = status
      this.code = code
    }
  },
  confirmPasswordReset: (...args: unknown[]) => confirmPasswordReset(...args),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({ isAuthenticated: false, logout }),
}))

import { AuthApiError } from '@/features/auth/api'
import { PasswordResetConfirmPage } from './password-reset-confirm-page'

function renderPage(initialHref: string) {
  const history = createMemoryHistory(initialHref)
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(AppRouteProvider, { history }, children)
  }
  render(createElement(PasswordResetConfirmPage), { wrapper: Wrapper })
  return { history }
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  confirmPasswordReset.mockReset()
  logout.mockReset()
  confirmPasswordReset.mockResolvedValue({ detail: 'ok' })
})

describe('PasswordResetConfirmPage', () => {
  it('moves the fragment secret into state and strips it from the URL', () => {
    const { history } = renderPage('/password-reset#confirm-token')
    expect(history.getHref()).toBe('/password-reset')
  })

  it('submits token with the new password pair', async () => {
    renderPage('/password-reset#confirm-token')
    const passwordInputs = screen.getAllByLabelText(/Mot de passe|Confirmer/)
    fireEvent.change(passwordInputs[0] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.change(passwordInputs[1] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await vi.waitFor(() => {
      expect(confirmPasswordReset).toHaveBeenCalledWith({
        token: 'confirm-token',
        password: 'AnotherSecurePass456!',
        password_confirmation: 'AnotherSecurePass456!',
      })
    })
  })

  it('keeps the form when password validation fails', async () => {
    confirmPasswordReset.mockRejectedValueOnce(
      new AuthApiError('This password is too common.', 400, null),
    )
    renderPage('/password-reset#confirm-token')
    const passwordInputs = screen.getAllByLabelText(/Mot de passe|Confirmer/)
    fireEvent.change(passwordInputs[0] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.change(passwordInputs[1] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await vi.waitFor(() => {
      expect(screen.getByText('This password is too common.')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: 'Enregistrer' })).toBeTruthy()
    expect(screen.getAllByLabelText(/Mot de passe|Confirmer/).length).toBeGreaterThan(0)
  })

  it('replaces the form when the reset token is invalid', async () => {
    confirmPasswordReset.mockRejectedValueOnce(
      new AuthApiError('This password reset request is not valid.', 400, 'password_reset_invalid'),
    )
    renderPage('/password-reset#confirm-token')
    const passwordInputs = screen.getAllByLabelText(/Mot de passe|Confirmer/)
    fireEvent.change(passwordInputs[0] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.change(passwordInputs[1] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await vi.waitFor(() => {
      expect(screen.getByText('Ce lien n’est plus valide.')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: 'Enregistrer' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeTruthy()
  })
})
