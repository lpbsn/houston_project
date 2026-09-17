// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ForgotPasswordPage } from './forgot-password-page'

const { requestPasswordReset } = vi.hoisted(() => ({
  requestPasswordReset: vi.fn(),
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
    requestPasswordReset: (...args: unknown[]) => requestPasswordReset(...args),
  }
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    requestPasswordReset.mockResolvedValue({ detail: 'ok' })
  })

  it('submits email and shows a generic success message', async () => {
    const onNavigate = vi.fn()
    render(<ForgotPasswordPage onNavigate={onNavigate} />)

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'live@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }))

    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith({ email: 'live@example.com' })
    })
    expect(
      screen.getByText(/Si un compte existe pour cette adresse/),
    ).toBeTruthy()
  })
})
