// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PasswordChangeCard } from './password-change-card'

const { changePassword, fetchBootstrap } = vi.hoisted(() => ({
  changePassword: vi.fn(),
  fetchBootstrap: vi.fn(),
}))

vi.mock('@/features/auth/api', async () => {
  class AuthApiErrorMock extends Error {
    status: number
    code: string | null
    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.name = 'AuthApiError'
      this.status = status
      this.code = code
    }
  }
  return {
    AuthApiError: AuthApiErrorMock,
    changePassword: (...args: unknown[]) => changePassword(...args),
    fetchBootstrap: (...args: unknown[]) => fetchBootstrap(...args),
  }
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('PasswordChangeCard', () => {
  beforeEach(() => {
    changePassword.mockResolvedValue(undefined)
    fetchBootstrap.mockResolvedValue(undefined)
  })

  it('sends current and new passwords then shows success', async () => {
    render(<PasswordChangeCard />)

    fireEvent.click(screen.getByRole('button', { name: 'Changer le mot de passe' }))
    fireEvent.change(screen.getByPlaceholderText('Mot de passe actuel'), {
      target: { value: 'SecurePass123!' },
    })
    const passwordInputs = screen.getAllByLabelText(/Mot de passe|Confirmer/) 
    fireEvent.change(passwordInputs[0] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.change(passwordInputs[1] as HTMLElement, {
      target: { value: 'AnotherSecurePass456!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith({
        current_password: 'SecurePass123!',
        password: 'AnotherSecurePass456!',
        password_confirmation: 'AnotherSecurePass456!',
      })
    })
    await waitFor(() => {
      expect(screen.getByText('Mot de passe mis à jour.')).toBeTruthy()
    })
  })
})
