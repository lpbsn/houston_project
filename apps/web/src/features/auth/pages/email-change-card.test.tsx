// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EmailChangeCard } from './email-change-card'

const { requestEmailChange, fetchBootstrap } = vi.hoisted(() => ({
  requestEmailChange: vi.fn(),
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
    requestEmailChange: (...args: unknown[]) => requestEmailChange(...args),
    fetchBootstrap: (...args: unknown[]) => fetchBootstrap(...args),
  }
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('EmailChangeCard', () => {
  beforeEach(() => {
    requestEmailChange.mockResolvedValue({
      pending_email: 'next@example.com',
      expires_at: '2026-09-18T10:00:00Z',
    })
    fetchBootstrap.mockResolvedValue(undefined)
  })

  it('sends password and new email then shows pending state', async () => {
    render(<EmailChangeCard email="live@example.com" pendingEmail={null} />)

    fireEvent.click(screen.getByRole('button', { name: 'Changer d’e-mail' }))
    fireEvent.change(screen.getByPlaceholderText('Mot de passe actuel'), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByPlaceholderText('Nouvelle adresse e-mail'), {
      target: { value: 'next@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }))

    await waitFor(() => {
      expect(requestEmailChange).toHaveBeenCalledWith({
        password: 'SecurePass123!',
        new_email: 'next@example.com',
      })
    })
    await waitFor(() => {
      expect(screen.getByText(/Confirmation en attente pour next@example.com/)).toBeTruthy()
    })
  })
})
